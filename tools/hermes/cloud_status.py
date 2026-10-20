"""Read-only cloud status report for task checkpoints on GitHub-hosted runners.

This module deliberately does not instantiate Hermes Agent or use provider tokens.
Its scheduled GitHub Actions job can run while all user devices are off.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

import checkpoint as cp


def git_head(root: Path) -> str:
    p = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True,
                       capture_output=True, check=False, timeout=15)
    if p.returncode:
        raise RuntimeError("No se puede obtener HEAD de git")
    sha = cp.clean_commit(p.stdout.strip())
    if not sha:
        raise RuntimeError("HEAD no disponible")
    return sha


def make_report(root: Path, head: str | None = None) -> dict:
    root = root.resolve(strict=True)
    head = cp.clean_commit(head) if head else git_head(root)
    folder = root / ".hermes" / "checkpoints"
    if not folder.is_dir():
        raise RuntimeError("No hay carpeta de checkpoints")
    files = sorted(folder.glob("*.json"))
    if not files:
        raise RuntimeError("No hay checkpoints")
    summaries = []
    for path in files:
        task = cp.load(path, path.stem)  # fail closed for corrupt JSON
        outcome = cp.resume(task, head)
        summaries.append({
            "task_id": task["task_id"],
            "project": task["project"],
            "branch": task["branch"],
            "status": task["status"],
            "checkpoint_updated": task["updated_at"],
            "last_observed_commit": task["last_observed_commit"],
            "last_verified_commit": task["last_verified_commit"],
            "next_action": task["next_action"],
            "blockers": task["blockers"],
            "incremental_review_required": outcome["incremental_review_required"],
            "verification_pending": outcome["verification_pending"],
        })
    return {
        "schema_version": 1,
        "mode": "read_only_cloud_monitor",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "head": head,
        "total": len(summaries),
        "tasks": summaries,
        "does_not_execute_ai": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DEXTER HERMES — estado nube sin PC")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = make_report(args.root)
        payload = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        if args.output:
            # Only ephemeral cloud reports; never write to the source tree.
            out = args.output.expanduser().resolve()
            root = args.root.resolve()
            if out == root or root in out.parents:
                raise ValueError("El reporte debe guardarse fuera del repositorio")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(payload, encoding="utf-8")
        print(payload)
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as e:
        print("HERMES Cloud Monitor: " + str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
