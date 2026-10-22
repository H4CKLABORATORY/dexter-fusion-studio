#!/usr/bin/env python3
"""Hermes cron --no-agent -> OpenCode CLI; durable bounded queue (stdlib only)."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import uuid

ROOT = Path(os.environ.get("DEXTER_AUTO_HOME") or
            (Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "DEXTER-AUTO"))
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,48}$")


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex[:8] + ".tmp")
    temp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temp, path)


def read(home):
    file = home / "tasks.json"
    if not file.exists():
        return {"schema": 1, "tasks": []}
    state = json.loads(file.read_text(encoding="utf-8"))
    if state.get("schema") != 1 or not isinstance(state.get("tasks"), list):
        raise ValueError("Invalid queue")
    return state


def command(argv, cwd, timeout=30):
    done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if done.returncode:
        raise RuntimeError(f"{argv[0]} returned {done.returncode}: {done.stderr[-400:]}")
    return done.stdout.strip()


def project_root(path):
    path = path.expanduser().resolve(strict=True)
    root = Path(command(["git", "rev-parse", "--show-toplevel"], path)).resolve(strict=True)
    if root != path:
        raise ValueError("Select the root folder of a Git repository")
    return root


def enqueue(home, project, prompt, name="", model="", timeout=1800, checks=None):
    project = project_root(project)
    if home.expanduser().resolve().is_relative_to(project):
        raise ValueError("State cannot be stored inside the project repository")
    if (home / "runner.lock").exists():
        raise RuntimeError("Runner is busy; add task after current run")
    if not prompt.strip() or len(prompt) > 12000 or not 30 <= timeout <= 3600:
        raise ValueError("Invalid prompt or timeout")
    checks = [] if checks is None else checks
    if not isinstance(checks, list) or len(checks) > 8 or any(
        not isinstance(v, list) or not 1 <= len(v) <= 12 or
        any(not isinstance(s, str) or not s or len(s) > 600 for s in v)
        for v in checks
    ):
        raise ValueError("Checks must be arrays of executable and arguments")
    name = name or "task-" + uuid.uuid4().hex[:10]
    if not ID.fullmatch(name):
        raise ValueError("Invalid task ID")
    state = read(home)
    if any(task.get("id") == name for task in state["tasks"]):
        raise ValueError("Task already queued")
    state["tasks"].append({
        "id": name, "project": str(project), "prompt": prompt.strip(), "model": model,
        "checks": checks, "timeout": timeout, "status": "pending", "queuedAt": now()
    })
    write(home / "tasks.json", state)
    return name


def execute(argv, cwd, log, timeout):
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as out:
        out.write(f"\n[{now()}] executing {Path(argv[0]).name}\n")
        out.flush()
        proc = subprocess.Popen(argv, cwd=str(cwd), stdout=out,
                                stderr=subprocess.STDOUT, start_new_session=os.name != "nt")
        try:
            return proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            proc.wait(timeout=15)
            raise TimeoutError(f"Executor timed out after {timeout} seconds")


def run_one(home):
    home.mkdir(parents=True, exist_ok=True)
    lock = home / "runner.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        print("Runner busy or stale lock; inspect runner.lock", file=sys.stderr)
        return 3
    os.close(fd)
    try:
        state = read(home)
        if any(t.get("status") == "running" for t in state["tasks"]):
            print("Interrupted task; manual worktree review required", file=sys.stderr)
            return 4
        task = next((t for t in state["tasks"] if t.get("status") == "pending"), None)
        if task is None:
            return 0  # silent tick with no pending job
        project = project_root(Path(task["project"]))
        opencode = shutil.which("opencode")
        if not opencode:
            raise RuntimeError("OpenCode CLI not on PATH")
        head = command(["git", "rev-parse", "HEAD"], project)
        nonce = uuid.uuid4().hex[:8]
        branch = f"agent/dexter-{task['id']}-{nonce}"
        worktree = home / "worktrees" / f"{task['id']}-{nonce}"
        worktree.parent.mkdir(parents=True, exist_ok=True)
        task.update(status="running", startedAt=now(), baseHead=head, branch=branch,
                    worktree=str(worktree), log=str(home / "logs" / f"{task['id']}-{nonce}.log"))
        write(home / "tasks.json", state)
        command(["git", "worktree", "add", "-b", branch, str(worktree), head], project, 90)
        policy = (
            "\n\nRead AGENTS.md and existing checkpoints when present. Work ONLY in this "
            "isolated Git worktree. Make a real reversible code improvement and execute "
            "relevant tests. Save CHECKPOINT-DEXTER.md with changed files, test results "
            "and next step. Never push, merge, deploy, access billing or touch secrets. "
            "A separate host process verifies changes and specified checks."
        )
        argv = [opencode, "run", "--agent", "build", "--format", "json"]
        if task.get("model"):
            argv.extend(["--model", task["model"]])
        argv.append(task["prompt"] + policy)
        exit_code = execute(argv, worktree, Path(task["log"]), int(task["timeout"]))
        if exit_code:
            raise RuntimeError(f"OpenCode returned {exit_code}; inspect task log")
        changed = command(["git", "status", "--porcelain", "--untracked-files=normal"], worktree)
        if not changed:
            raise RuntimeError("No changed files; work not verified")
        command(["git", "diff", "--check"], worktree)
        for check in task.get("checks", []):
            code = execute(check, worktree, Path(task["log"]), min(task["timeout"], 300))
            if code:
                raise RuntimeError(f"Check {check[0]} failed, code {code}")
        substantive = [v for v in task.get("checks", []) if v != ["git", "diff", "--check"]]
        task["status"] = "completed" if substantive else "needs_review"
        task["verification"] = "host_checks_passed" if substantive else "git_diff_only"
        task["changedFiles"] = changed.splitlines()[:200]
        task["finishedAt"] = now()
        write(home / "tasks.json", state)
        print(json.dumps({"id": task["id"], "status": task["status"], "worktree": str(worktree)}))
        return 0
    except Exception as exc:
        if "task" in locals() and task is not None and task.get("status") == "running":
            task.update(status="blocked", error=f"{type(exc).__name__}: {exc}"[:500], finishedAt=now())
            write(home / "tasks.json", state)
        print(f"DEXTER blocked: {exc}", file=sys.stderr)
        return 2
    finally:
        lock.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["run", "add", "status", "doctor"], nargs="?", default="run")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--project", type=Path)
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("--name", default="")
    parser.add_argument("--model", default="")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--checks-json", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == "doctor":
            print(json.dumps({"git": shutil.which("git"), "opencode": shutil.which("opencode"),
                              "state": str(args.root), "lock": (args.root / "runner.lock").exists()}))
            return 0 if shutil.which("git") and shutil.which("opencode") else 2
        if args.action == "status":
            for task in read(args.root)["tasks"]:
                print(f"{task['id']}: {task['status']} | {task.get('worktree','-')}")
            return 0
        if args.action == "add":
            if not args.project or not args.prompt_file:
                parser.error("add requires --project and --prompt-file")
            checks = json.loads(args.checks_json.read_text(encoding="utf-8")) if args.checks_json else []
            name = enqueue(args.root, args.project, args.prompt_file.read_text(encoding="utf-8"),
                           args.name, args.model, args.timeout, checks)
            print("Queued " + name)
            return 0
        return run_one(args.root)
    except Exception as exc:
        print(f"DEXTER error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
