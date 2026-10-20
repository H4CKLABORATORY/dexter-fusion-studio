"""Bounded DEXTER HERMES multi-project scheduler.

Run locally under systemd / Windows Task Scheduler; by default reports status only.
To run real agents: set HERMES_RUN_ENABLED=1 AND pass --execute.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time

import checkpoint as cp
import runner

MIN_INTERVAL = 300
MAX_TASKS_PER_CYCLE = 10


def read_manifest(filename: Path) -> list[tuple[Path, str]]:
    obj = json.loads(filename.read_text(encoding="utf-8"))
    if not isinstance(obj, dict) or obj.get("schema_version") != 1:
        raise runner.RunnerError("Manifiesto incompatible")
    projects = obj.get("projects")
    if not isinstance(projects, list) or not 1 <= len(projects) <= 20:
        raise runner.RunnerError("Manifiesto necesita entre 1 y 20 proyectos")
    tasks = []
    seen = set()
    for project in projects:
        if not isinstance(project, dict) or set(project) != {"root", "tasks"}:
            raise runner.RunnerError("Proyecto necesita root absoluto y tasks")
        if not isinstance(project["root"], str) or not project["root"].strip():
            raise runner.RunnerError("root debe ser ruta absoluta no vacía")
        root = Path(project["root"]).expanduser()
        if not root.is_absolute() or not root.is_dir():
            raise runner.RunnerError(f"Ruta no válida o inexistente: {root}")
        names = project["tasks"]
        if not isinstance(names, list) or not 1 <= len(names) <= 20:
            raise runner.RunnerError("Cada proyecto requiere 1 a 20 tareas")
        for name in names:
            cp.file_for(root, name)  # validates task ID
            key = (str(root.resolve()), name)
            if key in seen:
                raise runner.RunnerError("Tarea duplicada en el manifiesto")
            seen.add(key)
            tasks.append((root.resolve(), name))
    return tasks


def cycle(manifest: Path, *, execute: bool, max_runs: int, binary: str = "hermes",
          timeout: int = 900) -> dict:
    if not 1 <= max_runs <= MAX_TASKS_PER_CYCLE:
        raise runner.RunnerError("max-runs fuera de rango (1-10)")
    if execute and os.getenv(runner.ENV_ENABLE) != "1":
        raise runner.RunnerError(f"Se requiere {runner.ENV_ENABLE}=1")
    jobs = read_manifest(manifest)
    outcomes = []
    tried = 0
    for root, task in jobs:
        store = runner.state_root(root)
        try:
            snap = runner.one_tick(root, task, binary, store, timeout,
                                   enabled=False, execute=False)
            status = snap["resume"]["status"]
            if status in {"blocked", "completed"}:
                outcomes.append({"task": task, "result": "skipped", "reason": status})
                continue
            if not execute:
                outcomes.append({"task": task, "result": "ready",
                                 "diff_review": snap["resume"]["incremental_review_required"]})
                continue
            if tried >= max_runs:
                outcomes.append({"task": task, "result": "deferred", "reason": "cycle limit"})
                continue
            with runner.task_lock(store, "workspace"):
                # runner enforces opt-in and a second per-task lock.
                result = runner.one_tick(root, task, binary, store, timeout,
                                         enabled=True, execute=True)
                outcomes.append({"task": task, "result": result["mode"],
                                 "status": result.get("state"),
                                 "agent_completed": result.get("agent_completed", False)})
                tried += 1
        except (runner.RunnerError, FileNotFoundError, ValueError, OSError) as exc:
            outcomes.append({"task": task, "result": "error",
                             "error": str(exc)[:300]})
    return {"mode": "execute" if execute else "status",
            "attempted": tried, "tasks": outcomes}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="DEXTER HERMES — programador local seguro")
    p.add_argument("--config", type=Path, required=True,
                   help="JSON local que contiene rutas absolutas de repositorios")
    p.add_argument("--binary", default="hermes")
    p.add_argument("--execute", action="store_true")
    p.add_argument("--loop", action="store_true",
                   help="mantener el proceso activo, cada --interval-sec")
    p.add_argument("--interval-sec", type=int, default=3600)
    p.add_argument("--max-runs", type=int, default=1)
    p.add_argument("--timeout-sec", type=int, default=900)
    args = p.parse_args(argv)
    if args.loop and not MIN_INTERVAL <= args.interval_sec <= 86400:
        p.error("interval-sec debe estar entre 300 y 86400")
    if args.execute and os.getenv(runner.ENV_ENABLE) != "1":
        p.error(f"--execute también requiere {runner.ENV_ENABLE}=1")
    try:
        while True:
            result = cycle(args.config, execute=args.execute, max_runs=args.max_runs,
                           binary=args.binary, timeout=args.timeout_sec)
            print(json.dumps(result, ensure_ascii=False), flush=True)
            if not args.loop:
                return 0 if not any(x["result"] == "error" for x in result["tasks"]) else 2
            time.sleep(args.interval_sec)
    except KeyboardInterrupt:
        return 130
    except (ValueError, FileNotFoundError, runner.RunnerError, OSError, json.JSONDecodeError) as exc:
        print("HERMES Scheduler: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
