"""DEXTER HERMES: bounded, CPU-only cloud coding proposal worker.

The model receives only a fixed task specification, never repository credentials.
It may propose ONE new Python file within tools/hermes/experiments/.
Generated Python is syntax-parsed but never executed by this worker.
A separate credentialed GitHub Actions job opens a PR for human review.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import symtable
import sys
import urllib.error
import urllib.request

MAX_CODE_BYTES = 16_384
MAX_RESPONSE_BYTES = 64_000
MAX_GENERATION_ATTEMPTS = 3
OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"
MODEL_NAME = "qwen2.5-coder:1.5b"

TASKS = {
    "checkpoint-summary-helper": {
        "target": "tools/hermes/experiments/checkpoint_summary.py",
        "objective": (
            "Write a Python 3.11 stdlib-only reusable module that provides "
            "summarize_checkpoint(record: dict) -> dict. Input is a DEXTER HERMES "
            "checkpoint with fields task_id, project, status, next_action, blockers, "
            "last_observed_commit, last_verified_commit. Return a concise sanitized "
            "summary with keys task_id, project, status, next_action, blockers_count, "
            "verification_pending. Validate types and raise ValueError on invalid "
            "inputs. Add docstrings and type hints. Never access files, network, "
            "shell, environment variables, or third party modules."
        ),
    },
}
TASK_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")


class CloudWorkerError(RuntimeError):
    pass


def get_task(task_id: str) -> dict:
    if not isinstance(task_id, str) or not TASK_RE.fullmatch(task_id):
        raise CloudWorkerError("task_id inválido")
    if task_id not in TASKS:
        raise CloudWorkerError("Tarea no incluida en lista revisada")
    task = TASKS[task_id]
    target = PurePosixPath(task["target"])
    if target.is_absolute() or ".." in target.parts or target.suffix != ".py":
        raise CloudWorkerError("Ruta no permitida")
    if len(target.parts) != 4 or target.parts[:3] != ("tools", "hermes", "experiments"):
        raise CloudWorkerError("Solo experiments/ autorizado")
    return task


def build_prompt(task_id: str) -> str:
    task = get_task(task_id)
    return (
        "Generate ONLY a JSON object with exactly one property 'code'. "
        "The value must be plain Python 3.11 source, NOT Markdown or explanation. "
        "The entire module MUST consist of exactly one top-level function "
        "named summarize_checkpoint(record: dict) -> dict, with an optional "
        "module docstring. Do NOT include imports, from-imports, global "
        "variables, type aliases, classes, example calls, unit tests, "
        "if __name__ == '__main__', or setup code. Use only builtin "
        "types and methods. In the function validate input types, then "
        "return a dictionary. Do not read files, environment, network or "
        "execute commands. "
        "Task: " + task["objective"]
    )


def ollama_proposal(task_id: str, *, timeout: int = 360) -> str:
    if os.getenv("HERMES_CLOUD_MODEL_ENABLED") != "1":
        raise CloudWorkerError("Modelo deshabilitado; configurar HERMES_CLOUD_MODEL_ENABLED=1")
    prompt = build_prompt(task_id)
    messages = [
        {"role": "system", "content": (
            'Output only JSON {"code": "Python source"}. '
            "Exactly one top-level function; no import/assignment/examples at module scope."
        )},
        {"role": "user", "content": prompt},
    ]
    last_error = "Sin propuesta válida"
    for attempt in range(1, MAX_GENERATION_ATTEMPTS + 1):
        request_body = json.dumps({
            "model": MODEL_NAME,
            "messages": messages,
            "format": "json",
            "stream": False,
            "options": {"temperature": 0, "num_predict": 2000, "num_ctx": 4096},
        }).encode("utf-8")
        req = urllib.request.Request(
            OLLAMA_CHAT_URL, data=request_body, method="POST",
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
        except (urllib.error.URLError, TimeoutError) as exc:
            raise CloudWorkerError("No disponible el modelo local de Ollama") from exc
        if len(body) > MAX_RESPONSE_BYTES:
            raise CloudWorkerError("Respuesta del modelo demasiado larga")
        try:
            response_json = json.loads(body)
            generated_json = json.loads(response_json["message"]["content"])
            code = generated_json["code"]
            return sanitize_model_code(code)
        except (ValueError, KeyError, TypeError, CloudWorkerError) as exc:
            # Retry only model-output problems, never failing open or exposing
            # potentially unsafe generated code to logs.
            last_error = ("Respuesta del modelo sin JSON/code válido"
                          if isinstance(exc, (ValueError, KeyError, TypeError))
                          else str(exc)[:180])
            print(f"Cloud worker: intento {attempt}/{MAX_GENERATION_ATTEMPTS} rechazado: {last_error}",
                  file=sys.stderr)
            messages.append({"role": "user", "content": (
                "The previous output was rejected: " + last_error +
                ". Rewrite from scratch. JSON code string with ONE top-level "
                "summarize_checkpoint function, NO imports, classes, global "
                "assignments or examples. Nothing else."
            )})
    raise CloudWorkerError(
        f"Sin propuesta segura después de {MAX_GENERATION_ATTEMPTS} intentos: {last_error}"
    )

def sanitize_model_code(code: object) -> str:
    """Keep only an allowed function when a small model adds harmless scaffolding.

    Do not execute generated code or allow dependencies on any discarded imports,
    globals or helpers. validate_code stays strict for CI publishing.
    """
    if not isinstance(code, str):
        raise CloudWorkerError("El código debe ser texto")
    source = code.strip()
    if source.startswith("```python\n") and source.endswith("```"):
        source = source[len("```python\n"):-3].strip()
    elif source.startswith("```\n") and source.endswith("```"):
        source = source[4:-3].strip()
    # A clean module needs no normalization.
    try:
        return validate_code(source)
    except CloudWorkerError:
        pass
    if len(source.encode("utf-8")) > MAX_CODE_BYTES or "\x00" in source:
        raise CloudWorkerError("Propuesta no normalizable")
    try:
        original = ast.parse(source, filename="<model-proposal>")
    except SyntaxError as exc:
        raise CloudWorkerError("La propuesta Python no compila") from exc

    functions = [n for n in original.body if isinstance(n, ast.FunctionDef)
                 and n.name == "summarize_checkpoint"]
    if len(functions) != 1:
        raise CloudWorkerError("No hay una función única para recuperar")
    fn = functions[0]

    # Discard only simple, predictable extraneous module nodes. Anything that
    # could perform module-level actions remains a failure.
    for node in original.body:
        if node is fn:
            continue
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef)):
            continue  # stripped: even importing a module is NOT run
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            continue
        if isinstance(node, ast.Assign) and all(isinstance(t, ast.Name) for t in node.targets) and isinstance(node.value, ast.Constant):
            continue
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and (node.value is None or isinstance(node.value, ast.Constant)):
            continue
        if isinstance(node, ast.If) and _is_main_guard(node):
            continue
        raise CloudWorkerError("Código extra de nivel superior no recuperable")

    # A function decorator, default value or annotation expression may execute
    # at import time. Preserve only plain built-in type annotations.
    if fn.decorator_list or fn.args.defaults or any(v is not None for v in fn.args.kw_defaults):
        raise CloudWorkerError("Decoradores y parámetros por defecto no permitidos")
    for argument in (*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs):
        _check_annotation(argument.annotation)
    if fn.args.vararg:
        _check_annotation(fn.args.vararg.annotation)
    if fn.args.kwarg:
        _check_annotation(fn.args.kwarg.annotation)
    _check_annotation(fn.returns)

    cleaned = ast.unparse(ast.Module(body=[fn], type_ignores=[])) + "\n"
    verified = validate_code(cleaned)
    allowed_globals = {"dict", "str", "int", "bool", "list", "tuple", "set",
                       "isinstance", "len", "sorted", "min", "max", "sum",
                       "any", "all", "ValueError", "TypeError", "enumerate",
                       "range", "object"}
    symbols = symtable.symtable(verified, "<model-proposal>", "exec")
    for sub in symbols.get_children():
        if sub.get_name() == "summarize_checkpoint":
            for symbol in sub.get_symbols():
                if symbol.is_global() and symbol.is_referenced() and symbol.get_name() not in allowed_globals:
                    raise CloudWorkerError("Dependencia global no permitida en función recuperada")
    return verified


def _is_main_guard(node: ast.If) -> bool:
    test = node.test
    return (
        not node.orelse and isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name) and test.left.id == "__name__"
        and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)
        and len(test.comparators) == 1 and isinstance(test.comparators[0], ast.Constant)
        and test.comparators[0].value == "__main__"
    )


def _check_annotation(node: ast.expr | None) -> None:
    if node is None:
        return
    allowed = {"dict", "str", "int", "bool", "list", "tuple", "set", "object"}
    if isinstance(node, ast.Name) and node.id in allowed:
        return
    if isinstance(node, ast.Constant) and node.value is None:
        return
    raise CloudWorkerError("Anotación de tipo no permitida")


def validate_code(code: object) -> str:
    if not isinstance(code, str):
        raise CloudWorkerError("El código debe ser texto")
    source = code.strip() + "\n"
    encoded = source.encode("utf-8")
    if len(encoded) < 90 or len(encoded) > MAX_CODE_BYTES:
        raise CloudWorkerError("Tamaño de código fuera de límites")
    if "\x00" in source or "\r" in source:
        raise CloudWorkerError("Caracteres no permitidos")
    try:
        tree = ast.parse(source, filename="<model-proposal>")
    except SyntaxError as exc:
        raise CloudWorkerError("La propuesta Python no compila") from exc
    # Narrow pure-function prototype. No imports, no module-level actions,
    # no dynamic execution, no attributes with dunder names.
    allowed_top = (ast.FunctionDef, ast.Expr)
    if not all(isinstance(n, allowed_top) for n in tree.body):
        raise CloudWorkerError("Solo funciones y docstrings al nivel superior")
    for n in tree.body:
        if isinstance(n, ast.Expr) and not (
            isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)
        ):
            raise CloudWorkerError("Expresión global no permitida")
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if len(functions) != 1 or functions[0].name != "summarize_checkpoint":
        raise CloudWorkerError("La propuesta necesita exactamente summarize_checkpoint")

    forbidden = (ast.Import, ast.ImportFrom, ast.AsyncFunctionDef, ast.ClassDef,
                 ast.Lambda, ast.Global, ast.Nonlocal, ast.Yield, ast.YieldFrom,
                 ast.Await, ast.Try, ast.With)
    allowed_calls = {"isinstance", "len", "str", "int", "bool", "dict", "list",
                     "tuple", "set", "sorted", "min", "max", "sum", "any", "all",
                     "ValueError", "TypeError", "enumerate", "range"}
    safe_methods = {"get", "copy", "keys", "items", "values", "strip", "lower", "upper",
                    "startswith", "endswith", "count", "split", "join", "append"}
    for node in ast.walk(tree):
        if isinstance(node, forbidden):
            raise CloudWorkerError("Operación no admitida en propuesta")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise CloudWorkerError("Atributo interno prohibido")
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise CloudWorkerError("Nombre interno prohibido")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id not in allowed_calls:
                raise CloudWorkerError("Función no permitida")
            if isinstance(node.func, ast.Attribute) and node.func.attr not in safe_methods:
                raise CloudWorkerError("Método no permitido")
            if not isinstance(node.func, (ast.Name, ast.Attribute)):
                raise CloudWorkerError("Llamada dinámica no permitida")
    return source


def write_proposal(task_id: str, code: str, directory: Path) -> dict:
    task = get_task(task_id)
    # The output directory is an ephemeral artifact directory, never the repo.
    output = directory.resolve()
    if output.exists() and (output.is_symlink() or any(output.iterdir())):
        raise CloudWorkerError("El directorio de salida debe estar vacío")
    output.mkdir(parents=True, exist_ok=True)
    sanitized = validate_code(code)
    module_path = output / "proposal.py"
    module_path.write_text(sanitized, encoding="utf-8")
    report = {
        "schema_version": 1,
        "task_id": task_id,
        "target": task["target"],
        "sha256": hashlib.sha256(sanitized.encode("utf-8")).hexdigest(),
        "source": "Ollama local on ephemeral GitHub runner",
        "tests": "AST syntax and static restrictions only; runtime tests pending",
    }
    (output / "manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Hermes CPU cloud proposal generator")
    p.add_argument("--task-id", required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--generate", action="store_true")
    args = p.parse_args(argv)
    try:
        task = get_task(args.task_id)
        if not args.generate:
            print(json.dumps({"mode": "dry-run", "task_id": args.task_id,
                              "target": task["target"],
                              "prompt_sha256": hashlib.sha256(
                                  build_prompt(args.task_id).encode("utf-8")).hexdigest(),
                              "model": MODEL_NAME}, indent=2))
            return 0
        if not args.output:
            raise CloudWorkerError("--output obligatorio para generar")
        result = write_proposal(args.task_id, ollama_proposal(args.task_id), args.output)
        print(json.dumps(result, indent=2))
        return 0
    except (CloudWorkerError, OSError, ValueError) as exc:
        print("Cloud worker: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
