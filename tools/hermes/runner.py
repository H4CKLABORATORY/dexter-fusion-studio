"""DEXTER HERMES: finite, resumable local agent runner.

A run requires explicit opt-in and a configured Hermes Agent CLI.
No keys, model outputs or external commands are stored in the public repository.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Iterator

import checkpoint as cp

MAX_SECONDS = 3600
MAX_PROMPT_CHARS = 15000
PROTECTED = {"main", "master"}
ENV_ENABLE = "HERMES_RUN_ENABLED"


class RunnerError(RuntimeError):
    pass


def run_git(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                          timeout=15, check=False)
    if proc.returncode:
        raise RunnerError("No se pudo consultar git: " + " ".join(args))
    return proc.stdout.strip()


def inspect_repo(root: Path, *, execution: bool = False) -> dict:
    root = root.resolve(strict=True)
    top = Path(run_git(root, "rev-parse", "--show-toplevel")).resolve()
    if top != root:
        raise RunnerError("Usar la raíz real del repositorio, no un subdirectorio")
    branch = run_git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    commit = cp.clean_commit(run_git(root, "rev-parse", "HEAD"))
    if execution and branch in PROTECTED:
        raise RunnerError("Prohibido ejecutar agentes sobre main/master")
    if execution and run_git(root, "status", "--porcelain"):
        raise RunnerError("Árbol git sucio; confirmar o guardar cambios primero")
    return {"root": str(root), "branch": branch, "commit": commit}


def state_root(root: Path, override: Path | None = None) -> Path:
    if override is not None:
        resolved = override.expanduser().resolve()
        if resolved == root.resolve() or root.resolve() in resolved.parents:
            raise RunnerError("Los estados privados deben almacenarse fuera del repositorio")
        return resolved
    digest = hashlib.sha256(str(root.resolve()).encode("utf-8")).hexdigest()[:20]
    return Path.home() / ".dexter-hermes" / "workspaces" / digest


def task_state(root: Path, task_id: str, store: Path) -> tuple[Path, dict, bool]:
    # Validate task_id before looking up the template or state.
    in_repo = cp.file_for(root, task_id)
    private_file = cp.file_for(store, task_id)
    if private_file.exists():
        return private_file, cp.load(private_file, task_id), True
    if not in_repo.exists():
        raise RunnerError(f"Checkpoint no encontrado: {task_id}")
    return private_file, cp.load(in_repo, task_id), False


@contextmanager
def task_lock(store: Path, task_id: str) -> Iterator[None]:
    # Atomic directory creation gives single-writer behavior on local filesystems.
    lock_dir = store / "locks" / (task_id + ".lock")
    lock_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        lock_dir.mkdir()
    except FileExistsError as exc:
        raise RunnerError("Una ejecución ya tiene el bloqueo; revisar proceso antes de retirarlo") from exc
    try:
        (lock_dir / "owner.json").write_text(
            json.dumps({"pid": os.getpid(), "task_id": task_id, "at": cp.now()}),
            encoding="utf-8",
        )
        yield
    finally:
        (lock_dir / "owner.json").unlink(missing_ok=True)
        lock_dir.rmdir()


def prompt_for(data: dict, snapshot: dict) -> str:
    data = cp.check(data)
    if data["branch"] != snapshot["branch"]:
        raise RunnerError("Rama distinta de checkpoint; cambiar a la rama correcta")
    if data["status"] in {"blocked", "completed"}:
        raise RunnerError("Tarea bloqueada o completada; requiere revisión humana antes de repetir")
    resume = cp.resume(data, snapshot["commit"])
    message = f"""Eres un agente de programación ejecutado UNA VEZ en DEXTER HERMES.
Proyecto: {data['project']}
Tarea: {data['task_id']}
Objetivo: {data['objective']}
Acción siguiente: {data['next_action']}
Rama actual: {snapshot['branch']}
HEAD actual: {snapshot['commit']}
HEAD registrado: {data['last_observed_commit']}
Revisión incremental requerida: {resume['incremental_review_required']}
Pasos recientes: {json.dumps(resume['recent_steps'], ensure_ascii=False)}
Resultados de pruebas anteriores: {json.dumps(resume['recent_tests'], ensure_ascii=False)}

REGLAS:
- Lee AGENTS.md y los archivos relacionados con esta tarea, no reaudites todo de cero.
- Si existe un commit nuevo, revisa su diff y las pruebas pertinentes antes de editar.
- Trabaja solo en el árbol actual, en la rama no protegida indicada.
- No ejecutes git push, merge, rebase destructivo, ni acciones de red externas.
- No leas secretos, claves o carpetas privadas fuera del repositorio.
- No desactives aprobaciones ni utilices --yolo; solicita permiso si hace falta.
- Implementa a lo sumo una unidad de trabajo concreta y ejecuta pruebas.
- No declares tests aprobados ni trabajo completado sin evidencia.
- Deja la siguiente acción en .hermes/checkpoints o descríbela al finalizar.
- Si necesitas autorización, registra el bloqueo y termina. Responde en español.
"""
    if len(message) > MAX_PROMPT_CHARS:
        raise RunnerError("Prompt demasiado largo")
    return message


def one_tick(root: Path, task_id: str, binary: str, store: Path,
             timeout: int, enabled: bool, execute: bool) -> dict:
    if not execute:
        snap = inspect_repo(root)
        _, data, exists = task_state(root, task_id, store)
        return {"mode": "status", "workspace": snap, "private_checkpoint": exists,
                "resume": cp.resume(data, snap["commit"])}
    if not enabled:
        raise RunnerError(f"Para ejecutar configurar {ENV_ENABLE}=1 y pasar --execute")
    if not 10 <= timeout <= MAX_SECONDS:
        raise RunnerError("timeout fuera de rango (10 a 3600 segundos)")
    cmd = shutil.which(binary)
    if not cmd:
        raise RunnerError("Hermes CLI no encontrado. Instala y configura Hermes Agent.")
    snap = inspect_repo(root, execution=True)
    store = state_root(root, store)
    with task_lock(store, task_id):
        dest, data, _ = task_state(root, task_id, store)
        prompt = prompt_for(data, snap)
        # Persist running status before attempting any LLM call; never write secrets or
        # agent stdout to checkpoints (repositories may be public).
        data = cp.advance(data, status="in_progress",
                          next_action=data["next_action"], observed_commit=snap["commit"],
                          step="Ejecución local de Hermes preparada con bloqueo exclusivo")
        cp.save(dest, data)
        try:
            proc = subprocess.run(
                [cmd, "chat", "--oneshot", "--query-file", "-"],
                cwd=root, input=prompt, text=True, capture_output=True,
                timeout=timeout, check=False, env=os.environ.copy(),
            )
            after = inspect_repo(root)
            # Do not mark a code revision as verified solely from the Hermes process exit.
            success = proc.returncode == 0 and after["branch"] == snap["branch"]
            dirty = bool(run_git(root, "status", "--porcelain"))
            committed = after["commit"] != snap["commit"]
            # Never burn another model call hourly when a completed turn made no
            # persistent change, or when uncommitted changes need human inspection.
            progress = success and committed and not dirty
            followup = (
                "Revisar el nuevo commit, sus pruebas y el PR; registrar evidencia"
                if progress else
                "Revisar cambios no confirmados antes de reanudar"
                if success and dirty else
                "Hermes respondió sin un commit nuevo; revisar antes de repetir"
                if success else
                "Revisar ejecución local de Hermes y resolver bloqueo"
            )
            blocker = (
                None if progress else
                "Hay archivos modificados sin commit; revisar antes de otra ejecución"
                if success and dirty else
                "Sin commit nuevo; se evita una repetición automática sin progreso"
                if success else
                "Hermes CLI falló; revisar configuración local y permisos"
            )
            data = cp.advance(
                data, status="in_progress" if progress else "blocked",
                next_action=followup, observed_commit=after["commit"],
                step=("Hermes terminó y produjo un nuevo commit (CI pendiente)"
                      if progress else "Hermes terminó; se necesita revisión antes de continuar"),
                test_name="Hermes CLI exit", test_result="not_run",
                evidence=f"exit={proc.returncode}; stdout_sha256={hashlib.sha256(proc.stdout.encode()).hexdigest()}",
                blocker=blocker,
            )
            cp.save(dest, data)
            return {"mode": "executed", "task_id": task_id, "exit_code": proc.returncode,
                    "agent_completed": success, "progress_detected": bool(committed or dirty),
                    "state": data["status"], "next_action": data["next_action"],
                    "branch": after["branch"], "head": after["commit"],
                    "checkpoint": str(dest)}
        except subprocess.TimeoutExpired:
            data = cp.advance(data, status="blocked",
                              next_action="Revisar timeout de Hermes antes de reanudar",
                              blocker=f"Tiempo de ejecución agotado ({timeout}s)")
            cp.save(dest, data)
            return {"mode": "timeout", "task_id": task_id, "state": "blocked",
                    "checkpoint": str(dest)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DEXTER HERMES — ejecutar una tarea por tick")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--binary", default="hermes", help="CLI ejecutable de Hermes Agent")
    parser.add_argument("--state-dir", type=Path, help="carpeta PRIVADA externa al repo")
    parser.add_argument("--timeout-sec", type=int, default=900)
    parser.add_argument("--execute", action="store_true", help="ejecutar un solo turno Hermes")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        store = state_root(root, args.state_dir)
        result = one_tick(root, args.task_id, args.binary, store, args.timeout_sec,
                          enabled=os.getenv(ENV_ENABLE) == "1", execute=args.execute)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("mode") not in {"timeout"} and result.get("agent_completed", True) else 2
    except (RunnerError, ValueError, FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        print("HERMES: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
