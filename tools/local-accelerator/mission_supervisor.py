#!/usr/bin/env python3
"""DEXTER local mission supervisor (stdlib only).

Runs a finite, reviewed queue in a separate git worktree. Never pushes or merges.
Execution is deliberately local and must be started by the PC owner.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

HERE = Path(__file__).resolve().parent
DEFAULT_HOME = Path.home() / "DEXTER-LOCAL"
ID_RE = re.compile(r"^[a-z][a-z0-9-]{1,48}$")
VALID_KINDS = {"catalog_refresh", "qwen_catalog_review"}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def read_queue(path: Path) -> list[dict]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schemaVersion") != 1 or not isinstance(doc.get("tasks"), list) or not doc["tasks"]:
        raise ValueError("Queue must have schemaVersion=1 and nonempty tasks")
    seen = set()
    for task in doc["tasks"]:
        if not isinstance(task, dict) or set(task) - {"id", "kind", "timeoutSeconds"}:
            raise ValueError("Queue task has unexpected properties")
        ident, kind, timeout = task.get("id"), task.get("kind"), task.get("timeoutSeconds")
        if not isinstance(ident, str) or not ID_RE.fullmatch(ident) or ident in seen:
            raise ValueError("Invalid or duplicate task id")
        if kind not in VALID_KINDS or type(timeout) is not int or not 10 <= timeout <= 3600:
            raise ValueError("Unsupported task type or timeout")
        seen.add(ident)
    return doc["tasks"]


def git(args: list[str], cwd: Path, timeout: int = 30) -> str:
    cp = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False)
    if cp.returncode:
        raise RuntimeError(f"git {args[0]} failed: {cp.stderr.strip()[:600]}")
    return cp.stdout.strip()


def run(args: list[str], cwd: Path, timeout: int, log: Path, env: dict | None = None) -> int:
    """No shell; stdout redirected to disk; kill process tree on timeout."""
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"\n[{now()}] executable={Path(args[0]).name} timeout={timeout}s\n")
        stream.flush()
        proc = subprocess.Popen(args, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
                                env=env, start_new_session=os.name != "nt")
        try:
            return proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            else:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            proc.wait(timeout=15)
            raise TimeoutError(f"Process exceeded {timeout}s (see {log})")


def validate_catalog(path: Path) -> int:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or not isinstance(doc.get("groups"), dict):
        raise ValueError("Invalid catalog groups")
    when = doc.get("updated")
    if not isinstance(when, str):
        raise ValueError("Missing update timestamp")
    dt.datetime.fromisoformat(when.replace("Z", "+00:00"))
    total = 0
    for section, records in doc["groups"].items():
        if not isinstance(records, list):
            raise ValueError(f"Invalid group: {section}")
        seen = set()
        for record in records:
            if not isinstance(record, dict) or not record.get("id") or not record.get("title"):
                raise ValueError(f"Missing anime id/title in {section}")
            ident = str(record["id"])
            if ident in seen:
                raise ValueError(f"Duplicate id {ident} in {section}")
            seen.add(ident)
            links = record.get("streaming", [])
            if not isinstance(links, list):
                raise ValueError(f"Invalid streaming links in {section}")
            for item in links:
                if not isinstance(item, dict) or not isinstance(item.get("url"), str) or not item["url"].startswith("https://"):
                    raise ValueError(f"Non-HTTPS or invalid streaming link in {section}")
            total += 1
    if total < 5:
        raise ValueError("Catalog has fewer than 5 cards")
    return total


def model_id(endpoint: str) -> str:
    # Never allow endpoint pointing outside localhost; protects credentials, SSRF and surprises.
    if endpoint not in {"http://127.0.0.1:1234/v1/models", "http://localhost:1234/v1/models"}:
        raise ValueError("Only the LM Studio loopback endpoint is supported")
    with urllib.request.urlopen(endpoint, timeout=8) as resp:
        doc = json.load(resp)
    candidates = [str(m.get("id", "")) for m in doc.get("data", []) if isinstance(m, dict)]
    for mid in candidates:
        if "qwen" in mid.lower() and re.fullmatch(r"[\w.\-/:]+", mid):
            return mid
    raise RuntimeError("LM Studio does not report a loaded Qwen model")


def execute_task(task: dict, worktree: Path, log_path: Path, venv_python: Path, model_endpoint: str) -> dict:
    kind = task["kind"]
    limit = task["timeoutSeconds"]
    catalog = worktree / "data" / "catalog.json"
    script = worktree / "scripts" / "refresh-catalog.mjs"
    if not script.is_file():
        raise FileNotFoundError(f"Missing existing scraper: {script}")
    if kind == "catalog_refresh":
        before = None
        try:
            if catalog.exists():
                before = validate_catalog(catalog)
        except (ValueError, json.JSONDecodeError) as exc:
            before = f"invalid previous catalog: {exc}"
        code = run(["node", "--check", str(script)], worktree, 30, log_path)
        if code != 0:
            raise RuntimeError(f"node --check failed ({code})")
        code = run(["node", str(script)], worktree, limit, log_path)
        if code != 0:
            raise RuntimeError(f"AniList fetch failed ({code}); last snapshot preserved if scraper is atomic")
        after = validate_catalog(catalog)
        return {"beforeCards": before, "afterCards": after, "source": "AniList GraphQL metadata", "playbackVerified": False}
    if kind == "qwen_catalog_review":
        mid = model_id(model_endpoint)
        if not venv_python.is_file():
            raise FileNotFoundError(f"Aider Python not found: {venv_python}. Run START-DEXTER.ps1 -StartTask first to install the Aider environment, or install aider-chat in this venv.")
        instructions = (
            "Lee AGENTS.md, docs/PROJECT_CONTINUITY.md y scripts/refresh-catalog.mjs. "
            "Revisa el catalogo actualizado y detecta UN defecto REAL y reproducible de metadatos. "
            "Si existe, corrige lo minimo dentro de este worktree; no inventes episodios ni enlaces de video. "
            "Si no hay fallo, NO cambies codigo y describe la evidencia. "
            "No ejecutes comandos de shell, no modifiques autenticacion, secretos, despliegue ni fuentes de reproduccion. "
            "No hagas git push, commits ni merges."
        )
        env = os.environ.copy()
        env.update({"OPENAI_API_BASE": "http://127.0.0.1:1234/v1", "OPENAI_API_KEY": "lm-studio"})
        cmd = [str(venv_python), "-m", "aider", "--model", "openai/" + mid,
               "--yes-always", "--no-auto-commits", "--no-suggest-shell-commands", "--message", instructions,
               "--read", "AGENTS.md", "--read", "docs/PROJECT_CONTINUITY.md",
               "scripts/refresh-catalog.mjs"]
        code = run(cmd, worktree, limit, log_path, env)
        if code != 0:
            raise RuntimeError(f"Aider exited with code {code}")
        code = run(["node", "--check", str(script)], worktree, 30, log_path)
        if code != 0:
            raise RuntimeError(f"Post-Aider scraper syntax check failed ({code})")
        return {"model": mid, "syntaxCheck": "passed", "playbackVerified": False}
    raise ValueError(f"Unsupported task type: {kind}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=DEFAULT_HOME / "1UP-ANIME")
    parser.add_argument("--state-root", type=Path, default=DEFAULT_HOME / "supervisor")
    parser.add_argument("--queue", type=Path, default=HERE / "mission_queue.json")
    parser.add_argument("--max-tasks", type=int, default=2)
    parser.add_argument("--aider-python", type=Path, default=DEFAULT_HOME / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
    parser.add_argument("--model-endpoint", default="http://127.0.0.1:1234/v1/models")
    parser.add_argument("--plan", action="store_true", help="Validate config; do not create worktree or execute")
    parser.add_argument("--resume", action="store_true", help="Resume pending tasks in last worktree; stop on previous failures")
    args = parser.parse_args(argv)
    if not 1 <= args.max_tasks <= 25:
        parser.error("--max-tasks must be between 1 and 25")
    tasks = read_queue(args.queue)
    if args.plan:
        print(json.dumps({"project": str(args.project), "tasks": tasks[:args.max_tasks], "dryRun": True}, indent=2))
        return 0
    root = args.state_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock = root / "running.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        print(f"Another run or stale lock exists: {lock}. Inspect before manually removing.", file=sys.stderr)
        return 2
    os.close(fd)
    try:
        project = args.project.resolve(strict=True)
        if Path(git(["rev-parse", "--show-toplevel"], project)).resolve() != project:
            raise RuntimeError("--project must point to the repository root")
        head = git(["rev-parse", "HEAD"], project)
        active_file = root / "active.json"
        if args.resume:
            state = json.loads(active_file.read_text(encoding="utf-8"))
            if state.get("baseProject") != str(project) or state.get("queue") != str(args.queue.resolve()):
                raise RuntimeError("Resume project or queue differs from saved state")
            worktree = Path(state["worktree"])
            if not worktree.is_dir() or Path(git(["rev-parse", "--show-toplevel"], worktree)).resolve() != worktree.resolve():
                raise RuntimeError("Saved worktree is missing or invalid")
        else:
            run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
            branch = "agent/dexter-" + run_id
            worktree = root / "worktrees" / run_id
            worktree.parent.mkdir(parents=True, exist_ok=True)
            git(["worktree", "add", "-b", branch, str(worktree), head], project, timeout=60)
            state = {"runId": run_id, "baseProject": str(project), "baseCommit": head,
                     "queue": str(args.queue.resolve()), "branch": branch, "worktree": str(worktree),
                     "createdAt": now(), "updatedAt": now(), "status": "running", "tasks": {}}
            write_json(active_file, state)
        completed = 0
        for task in tasks:
            if completed >= args.max_tasks:
                break
            ident = task["id"]
            previous = state["tasks"].get(ident, {})
            if previous.get("status") == "passed":
                continue
            if previous.get("status") in {"failed", "timed_out", "running"}:
                raise RuntimeError(f"Previous task {ident} failed; inspect {active_file} before retrying (no silent reruns of AI edits)")
            record = {"status": "running", "startedAt": now(), "kind": task["kind"], "timeoutSeconds": task["timeoutSeconds"]}
            state["tasks"][ident] = record
            state["updatedAt"] = now()
            write_json(active_file, state)
            log = root / "logs" / (state["runId"] + "-" + ident + ".log")
            try:
                result = execute_task(task, worktree, log, args.aider_python, args.model_endpoint)
                record.update({"status": "passed", "result": result})
            except Exception as exc:
                record.update({"status": "timed_out" if isinstance(exc, TimeoutError) else "failed", "error": str(exc)})
                state["status"] = "blocked"
                raise
            finally:
                record["finishedAt"] = now()
                record["log"] = str(log)
                state["updatedAt"] = now()
                state["gitStatus"] = git(["status", "--porcelain"], worktree)
                write_json(active_file, state)
            completed += 1
        if state["status"] != "blocked":
            remaining = [t for t in tasks if state["tasks"].get(t["id"], {}).get("status") != "passed"]
            state["status"] = "paused" if remaining else "completed"
            state["updatedAt"] = now()
            write_json(active_file, state)
        print(json.dumps({"status": state["status"], "branch": state["branch"], "worktree": str(worktree),
                          "completedThisRun": completed, "checkpoint": str(active_file)}, indent=2))
        return 0
    except Exception as exc:
        print(f"DEXTER supervisor blocked: {exc}", file=sys.stderr)
        return 1
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
