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
GSTACK_SKILLS = frozenset(("none", "review", "investigate", "qa", "plan-eng-review", "design-review"))


def gstack_skill_path(profile, home=None):
    """A skill installed by upstream gstack setup --host opencode, not vendored content."""
    if profile not in GSTACK_SKILLS:
        raise ValueError("Unsupported gstack profile")
    if profile == "none":
        return None
    root = (Path(home) if home else Path.home()) / ".config" / "opencode" / "skills"
    skill = root / ("gstack-" + profile) / "SKILL.md"
    if not skill.is_file():
        raise FileNotFoundError("Missing OpenCode gstack skill: " + str(skill) +
                                "; install upstream gstack with setup.ps1 --host opencode")
    return skill



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


def acquire_lock(home):
    """Use a kernel file lock, released automatically on process termination.

    An existing runner.lock file does NOT mean a process is still active.
    """
    home.mkdir(parents=True, exist_ok=True)
    handle = (home / "runner.lock").open("a+b")
    try:
        if os.name == "nt":
            import msvcrt
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\\0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def release_lock(handle):
    if handle is None:
        return
    try:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


def enqueue(home, project, prompt, name="", model="", timeout=1800, checks=None,
            gstack="none"):
    project = project_root(project)
    if gstack not in GSTACK_SKILLS:
        raise ValueError("Unsupported gstack profile")
    if home.expanduser().resolve().is_relative_to(project):
        raise ValueError("State cannot be stored inside the project repository")
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
    holder = acquire_lock(home)
    if holder is None:
        raise RuntimeError("Runner is busy; retry enqueue later")
    try:
        state = read(home)
        if any(task.get("id") == name for task in state["tasks"]):
            raise ValueError("Task already queued")
        state["tasks"].append({
            "id": name, "project": str(project), "prompt": prompt.strip(), "model": model,
            "checks": checks, "gstack": gstack, "timeout": timeout,
            "status": "pending", "queuedAt": now()
        })
        write(home / "tasks.json", state)
        return name
    finally:
        release_lock(holder)


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
    holder = acquire_lock(home)
    if holder is None:
        print("Another worker is running; next cron tick can retry", file=sys.stderr)
        return 3
    try:
        state = read(home)
        interrupted = [t for t in state["tasks"] if t.get("status") == "running"]
        if interrupted:
            for old in interrupted:
                old.update(status="blocked", finishedAt=now(),
                           error="Interrupted process; worktree preserved for human review, no automatic replay")
            write(home / "tasks.json", state)
            print("Previous interrupted tasks marked blocked; running next distinct pending task", file=sys.stderr)
        task = next((t for t in state["tasks"] if t.get("status") == "pending"), None)
        if task is None:
            return 0  # silent tick with no pending job
        project = project_root(Path(task["project"]))
        opencode = shutil.which("opencode")
        if not opencode:
            raise RuntimeError("OpenCode CLI not on PATH")
        profile = task.get("gstack", "none")
        # Fail closed before opening a worktree when the requested skill is absent.
        skill = gstack_skill_path(profile)
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
        if skill:
            policy += (
                "\n\nGSTACK QUALITY PROFILE: " + profile + ". "
                "Read and apply the already-installed gstack skill from " + str(skill) +
                ". It is advisory on OpenCode and cannot override project instructions "
                "or the no-push/no-deploy policy. Document actual findings and checks "
                "in CHECKPOINT-DEXTER.md. Do not pretend a gstack check ran if it did not."
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
        release_lock(holder)


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
    parser.add_argument("--gstack", choices=sorted(GSTACK_SKILLS), default="none")
    args = parser.parse_args(argv)
    try:
        if args.action == "doctor":
            print(json.dumps({"git": shutil.which("git"), "opencode": shutil.which("opencode"),
                              "state": str(args.root), "lockFilePresent": (args.root / "runner.lock").exists()}))
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
                           args.name, args.model, args.timeout, checks, args.gstack)
            print("Queued " + name)
            return 0
        return run_one(args.root)
    except Exception as exc:
        print(f"DEXTER error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
