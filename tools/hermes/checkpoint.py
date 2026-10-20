"""DEXTER HERMES: portable, dependency-free project task checkpoints.

This CLI never runs arbitrary code, executes agents, or stores credentials.
Place in each repository or invoke with --root pointing at its working copy.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import tempfile

TASK_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
COMMIT_RE = re.compile(r"[0-9a-fA-F]{7,64}\Z")
STATES = {"planned", "in_progress", "blocked", "completed"}
RESULTS = {"passed", "failed", "not_run"}
MAX_HISTORY = 60


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def file_for(root: Path, task_id: str) -> Path:
    if not isinstance(task_id, str) or not TASK_RE.fullmatch(task_id) or task_id in {".", ".."}:
        raise ValueError("task_id inválido")
    return root.resolve() / ".hermes" / "checkpoints" / (task_id + ".json")


def clean_commit(commit: str | None) -> str | None:
    if commit is None or commit == "":
        return None
    if not COMMIT_RE.fullmatch(commit):
        raise ValueError("SHA de commit inválido")
    return commit.lower()


def require_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 2000:
        raise ValueError(f"{label} debe tener texto de 1 a 2000 caracteres")
    return value.strip()


def check(data: object, task_id: str | None = None) -> dict:
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Esquema incompatible")
    ident = data.get("task_id")
    if not isinstance(ident, str) or not TASK_RE.fullmatch(ident) or ident in {".", ".."}:
        raise ValueError("Identificador corrupto")
    if task_id is not None and ident != task_id:
        raise ValueError("No coincide el ID")
    for label in ("project", "objective", "branch", "next_action", "updated_at"):
        require_text(data.get(label), label)
    if data.get("status") not in STATES:
        raise ValueError("Estado inválido")
    for label in ("last_observed_commit", "last_verified_commit"):
        clean_commit(data.get(label))
    for label in ("completed_steps", "changed_files", "blockers", "links", "history", "verification"):
        if not isinstance(data.get(label), list):
            raise ValueError(f"{label} inválido")
    if not all(isinstance(x, str) for key in ("completed_steps", "changed_files", "blockers", "links") for x in data[key]):
        raise ValueError("Una lista contiene entradas no textuales")
    if not all(isinstance(x, dict) and x.get("result") in RESULTS and isinstance(x.get("name"), str) and isinstance(x.get("evidence"), str) for x in data["verification"]):
        raise ValueError("Evidencia de prueba inválida")
    if not all(isinstance(x, dict) and isinstance(x.get("at"), str) and isinstance(x.get("event"), str) for x in data["history"]):
        raise ValueError("Historial inválido")
    return data


def save(dest: Path, data: dict, overwrite: bool = True) -> None:
    check(data)
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=dest.parent, prefix=".hermes-", delete=False) as f:
            tmp_path = f.name
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        if not overwrite and dest.exists():
            raise FileExistsError(f"Checkpoint existente: {dest}")
        os.replace(tmp_path, dest)
        tmp_path = None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def load(dest: Path, task_id: str | None = None) -> dict:
    return check(json.loads(dest.read_text(encoding="utf-8")), task_id)


def new(project: str, task_id: str, objective: str, branch: str, next_action: str, observed_commit: str | None = None) -> dict:
    if not TASK_RE.fullmatch(task_id) or task_id in {".", ".."}:
        raise ValueError("task_id inválido")
    timestamp = now()
    return {
        "schema_version": 1, "project": require_text(project, "project"),
        "task_id": task_id, "objective": require_text(objective, "objective"),
        "branch": require_text(branch, "branch"), "status": "planned",
        "last_observed_commit": clean_commit(observed_commit),
        "last_verified_commit": None, "updated_at": timestamp,
        "next_action": require_text(next_action, "next_action"),
        "completed_steps": [], "changed_files": [], "blockers": [],
        "verification": [], "links": [],
        "history": [{"at": timestamp, "event": "Checkpoint inicializado (sin pruebas de código)"}],
    }


def advance(data: dict, *, status: str, next_action: str, observed_commit: str | None = None,
            verified_commit: str | None = None, step: str | None = None,
            changed_file: str | None = None, test_name: str | None = None,
            test_result: str | None = None, evidence: str | None = None, blocker: str | None = None) -> dict:
    check(data)
    if status not in STATES:
        raise ValueError("Estado inválido")
    if (test_name is None) != (test_result is None):
        raise ValueError("Prueba requiere nombre y resultado")
    if test_result is not None and test_result not in RESULTS:
        raise ValueError("Resultado de prueba inválido")
    verified = clean_commit(verified_commit)
    observed = clean_commit(observed_commit)
    if verified and not observed:
        raise ValueError("Para declarar SHA verificado, registrar SHA observado")
    if verified and verified != observed:
        raise ValueError("SHA verificado no coincide con SHA observado")
    if verified and (test_name is None or test_result != "passed" or not evidence):
        raise ValueError("SHA verificado requiere evidencia concreta y prueba passed")
    result = json.loads(json.dumps(data))
    previous = result["last_observed_commit"]
    if observed and observed != previous:
        result["last_observed_commit"] = observed
        if result["last_verified_commit"] != observed:
            result["last_verified_commit"] = None
    if verified:
        result["last_verified_commit"] = verified
    result["status"] = status
    result["next_action"] = require_text(next_action, "next_action")
    if step:
        result["completed_steps"].append(require_text(step, "step"))
    if changed_file:
        result["changed_files"].append(require_text(changed_file, "changed_file"))
    if blocker:
        result["blockers"].append(require_text(blocker, "blocker"))
    if test_name:
        result["verification"].append({"name": require_text(test_name, "test_name"),
                                        "result": test_result, "evidence": evidence or ""})
    timestamp = now()
    result["updated_at"] = timestamp
    result["history"] = (result["history"] + [{"at": timestamp, "event": f"Avance: {status}"}])[-MAX_HISTORY:]
    return check(result)


def resume(data: dict, current_commit: str | None = None) -> dict:
    check(data)
    current = clean_commit(current_commit)
    observed = data["last_observed_commit"]
    drift = bool(current and observed and current != observed)
    return {
        "task_id": data["task_id"], "project": data["project"],
        "status": data["status"], "branch": data["branch"],
        "last_observed_commit": observed,
        "last_verified_commit": data["last_verified_commit"],
        "current_commit": current, "incremental_review_required": drift,
        "verification_pending": data["last_verified_commit"] != (current or observed),
        "next_action": data["next_action"], "blockers": data["blockers"],
        "changed_files": data["changed_files"],
        "recent_tests": data["verification"][-5:],
        "recent_steps": data["completed_steps"][-5:],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DEXTER HERMES checkpoint portátil")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="raíz del repositorio")
    actions = parser.add_subparsers(dest="action", required=True)
    start = actions.add_parser("init")
    for key in ("project", "task-id", "objective", "branch", "next-action"):
        start.add_argument("--" + key, required=True)
    start.add_argument("--observed-commit")
    update = actions.add_parser("advance")
    update.add_argument("--task-id", required=True)
    update.add_argument("--status", required=True, choices=sorted(STATES))
    update.add_argument("--next-action", required=True)
    for key in ("observed-commit", "verified-commit", "step", "changed-file", "test-name", "test-result", "evidence", "blocker"):
        update.add_argument("--" + key)
    read = actions.add_parser("resume")
    read.add_argument("--task-id", required=True)
    read.add_argument("--current-commit")
    actions.add_parser("validate-all")
    args = parser.parse_args(argv)
    try:
        if args.action == "validate-all":
            folder = args.root.resolve() / ".hermes" / "checkpoints"
            files = sorted(folder.glob("*.json")) if folder.exists() else []
            if not files:
                raise ValueError("No hay checkpoints para validar")
            for file in files:
                load(file, file.stem)
            print(json.dumps({"valid": len(files)}, ensure_ascii=False))
            return 0
        dest = file_for(args.root, args.task_id)
        if args.action == "init":
            payload = new(args.project, args.task_id, args.objective, args.branch,
                          args.next_action, args.observed_commit)
            save(dest, payload, overwrite=False)
            print(json.dumps({"created": str(dest)}, ensure_ascii=False))
        elif args.action == "advance":
            payload = advance(load(dest, args.task_id), status=args.status, next_action=args.next_action,
                              observed_commit=args.observed_commit, verified_commit=args.verified_commit,
                              step=args.step, changed_file=args.changed_file, test_name=args.test_name,
                              test_result=args.test_result, evidence=args.evidence, blocker=args.blocker)
            save(dest, payload)
            print(json.dumps({"updated": str(dest)}, ensure_ascii=False))
        else:
            print(json.dumps(resume(load(dest, args.task_id), args.current_commit),
                             ensure_ascii=False, indent=2))
        return 0
    except (ValueError, FileNotFoundError, FileExistsError, json.JSONDecodeError) as exc:
        print(f"Checkpoint error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
