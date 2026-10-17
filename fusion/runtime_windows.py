"""Windows run-time bootstrap and diagnostics for frozen PyInstaller builds."""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

APP_VERSION = "0.3.0"


def ffmpeg_search_dirs():
    """Prefer the binaries distributed beside the installed executable."""
    if getattr(sys, "frozen", False):
        root = Path(sys.executable).resolve().parent
    else:
        root = Path(__file__).resolve().parents[1]
    candidates = [
        root / "bin",
        root / "ffmpeg" / "bin",
        root / "_internal" / "bin",
    ]
    extracted = getattr(sys, "_MEIPASS", None)
    if extracted:
        candidates += [Path(extracted)/"bin"]
    return candidates


def configure_runtime():
    """Subprocesses spawned by the editor see bundled FFmpeg and its DLLs."""
    for directory in ffmpeg_search_dirs():
        if (directory / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")).is_file():
            os.environ["PATH"] = str(directory) + os.pathsep + os.environ.get("PATH","")
            break


def environment_report():
    configure_runtime()
    def found(lib):
        try:
            return importlib.util.find_spec(lib) is not None
        except (ImportError, ValueError):
            return False
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    return {
        "app": "Dexter Fusion Studio",
        "version": APP_VERSION,
        "windows": os.name == "nt",
        "packaged": bool(getattr(sys, "frozen", False)),
        "ffmpeg_found": bool(ffmpeg),
        "ffprobe_found": bool(ffprobe),
        "ffmpeg_path": ffmpeg,
        "transcription_library": found("faster_whisper"),
        "whisper_model": "tiny (descarga opcional al primer uso; no viene con el instalador)",
        "ollama": "Opcional: requiere instalar Ollama y un modelo visual compatible",
        "api_openai": "Desactivada por defecto, requiere clave propia y aprobación",
        "ready_for_base_editing": bool(ffmpeg and ffprobe),
        "notes": "La compatibilidad final con Windows requiere prueba en la PC del usuario.",
    }


def self_check():
    report = environment_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready_for_base_editing"] else 2
