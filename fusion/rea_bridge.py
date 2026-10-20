"""Optional local REA (Reverse Engineer Anything) CLI adapter.

This module does not install REA, analyze anything automatically or upload
source/binaries. It requires the user to install and authorize REA separately.
"""

import json
import shutil
import subprocess
from pathlib import Path


class REAError(RuntimeError):
    """REA was unavailable or failed to return a usable analysis."""


def find_rea(executable=None):
    """Return a verified absolute path to the installed `rea` CLI."""
    candidate = str(executable) if executable else "rea"
    path = Path(candidate).expanduser()
    if not path.is_file():
        found = shutil.which(candidate)
        if not found:
            raise FileNotFoundError(
                "REA no está instalado. Consulta https://github.com/morluto/rea "
                "y ejecuta 'npx rea-agents setup' en tu equipo, con Node.js compatible."
            )
        path = Path(found)
    return str(path.resolve())


def _run_json(args, *, executable=None, timeout=120):
    if not 1 <= timeout <= 3600:
        raise ValueError("timeout debe estar entre 1 y 3600 segundos")
    command = [find_rea(executable), *args, "--json"]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8",
            errors="replace", shell=False, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise REAError(f"REA superó el tiempo límite de {timeout} segundos") from exc
    except OSError as exc:
        raise REAError(f"No se pudo iniciar REA: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "Error sin detalle")[-1600:]
        raise REAError(f"REA terminó con código {result.returncode}: {detail}")
    try:
        return json.loads(result.stdout)
    except (ValueError, TypeError) as exc:
        raise REAError("REA no devolvió JSON válido") from exc


def doctor(*, executable=None, timeout=45):
    """Read REA's real diagnostic report (without modifying agent config)."""
    return _run_json(["doctor"], executable=executable, timeout=timeout)


def analyze_javascript_application(target, *, executable=None, timeout=240):
    """Analyze an existing local JS/Electron directory or .asar file.

    No arbitrary shell arguments, shell interpolation, or auto-downloads are used.
    REA's evidence and caveats are returned unmodified to the caller.
    """
    path = Path(target).expanduser().resolve(strict=True)
    if not (path.is_dir() or (path.is_file() and path.suffix.lower() == ".asar")):
        raise ValueError("El objetivo debe ser una carpeta JS/Electron o archivo .asar")
    return _run_json(
        ["analyze-javascript-application", str(path)],
        executable=executable, timeout=timeout,
    )
