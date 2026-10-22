"""Planificador multiagente determinista: sin ejecución de código ni acceso remoto.

Convierte tareas con dependencias en propuestas para la cola existente de HERMES.
No presume que Locally Uncensored exponga una API; usa solo motores verificados.
"""
import argparse
import json
from pathlib import Path

ROLES = frozenset(("planner", "frontend", "backend", "reviewer", "qa", "researcher"))
MAX_TASKS = 64


def plan(spec):
    if not isinstance(spec, dict) or set(spec) != {"tasks"}:
        raise ValueError("Se requiere objeto con tasks")
    tasks = spec["tasks"]
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= MAX_TASKS:
        raise ValueError("Cantidad de tareas inválida")
    seen = {}
    for task in tasks:
        if not isinstance(task, dict) or set(task) != {"id", "role", "prompt", "depends_on"}:
            raise ValueError("Esquema de tarea inválido")
        ident, role, prompt, deps = (task[k] for k in ("id", "role", "prompt", "depends_on"))
        if not isinstance(ident, str) or not ident.isidentifier() or len(ident) > 64 or ident in seen:
            raise ValueError("ID inválido o duplicado")
        if role not in ROLES or not isinstance(prompt, str) or not 0 < len(prompt) <= 8000:
            raise ValueError("Rol o prompt inválido")
        if not isinstance(deps, list) or any(not isinstance(x, str) for x in deps) or len(set(deps)) != len(deps):
            raise ValueError("Dependencias inválidas")
        seen[ident] = task
    if any(dep not in seen for task in tasks for dep in task["depends_on"]):
        raise ValueError("Dependencia desconocida")
    pending = dict(seen)
    completed = set()
    batches = []
    while pending:
        ready = [task for task in pending.values() if set(task["depends_on"]) <= completed]
        if not ready:
            raise ValueError("Dependencias cíclicas")
        batches.append(ready)
        completed.update(task["id"] for task in ready)
        for task in ready:
            del pending[task["id"]]
    return batches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path, help="Archivo JSON con tareas y dependencias")
    args = parser.parse_args()
    batches = plan(json.loads(args.spec.read_text(encoding="utf-8")))
    print(json.dumps({"batches": batches, "execution": "planning-only",
                      "note": "Requiere verificación de motores y aprobación antes de ejecutar"},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
