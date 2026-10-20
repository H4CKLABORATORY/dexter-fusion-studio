"""TokenLab for Dexter Fusion Studio: exact OpenAI text tokens and atomic checkpoints.

Only counts supplied text. Hidden chat framing, tool schemas, images and audio are additional.
No native local-model counts are claimed via an OpenAI tokenizer.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

class TokenLabUnavailable(RuntimeError):
    """The matching official tokenization dependency is not available."""

def counter_for_model(model: str = "gpt-4o"):
    """Return tiktoken's official OpenAI encoding, or fail explicitly."""
    try:
        import tiktoken
    except ImportError as exc:
        raise TokenLabUnavailable("Instala tiktoken en el entorno Python del Studio") from exc
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError as exc:
        raise TokenLabUnavailable("Tokenizador no identificado para este modelo") from exc

def compare_texts(a: str, b: str, model: str = "gpt-4o") -> dict:
    """Compare exact text token counts, never estimated word counts."""
    if not isinstance(a, str) or not isinstance(b, str):
        raise TypeError("Los dos prompts deben ser texto")
    enc = counter_for_model(model)
    before, after = len(enc.encode(a)), len(enc.encode(b))
    return {"model": model, "encoding": enc.name, "a_tokens": before,
            "b_tokens": after, "difference": after - before,
            "savings": before - after,
            "savings_pct": round((before-after)*100/before,2) if before else 0.0}

class AtomicTaskCheckpoint:
    """Atomic per-task JSON state, stored outside the public source tree."""
    def __init__(self, folder: str | Path | None = None):
        self.folder = Path(folder) if folder else Path.home() / "Documents" / "DexterFusionStudio" / "tokenlab"

    def _path(self, task_id: str) -> Path:
        if not isinstance(task_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}",task_id):
            raise ValueError("task_id inválido")
        return self.folder / (task_id + ".json")

    def save(self, task_id: str, state: dict) -> Path:
        if not isinstance(state, dict):
            raise TypeError("El estado debe ser un objeto JSON")
        dest = self._path(task_id)
        raw = json.dumps({"task_id":task_id,"state":state},ensure_ascii=False,
                         allow_nan=False,sort_keys=True).encode("utf-8")
        dest.parent.mkdir(parents=True,exist_ok=True)
        filename=None
        try:
            with tempfile.NamedTemporaryFile(dir=dest.parent,prefix=".tokenlab-",delete=False) as f:
                filename=f.name
                f.write(raw); f.flush(); os.fsync(f.fileno())
            os.replace(filename,dest)
            return dest
        finally:
            if filename and os.path.exists(filename):
                os.unlink(filename)

    def load(self, task_id: str) -> dict | None:
        dest=self._path(task_id)
        if not dest.exists():
            return None
        payload=json.loads(dest.read_text(encoding="utf-8"))
        if payload.get("task_id") != task_id or not isinstance(payload.get("state"),dict):
            raise ValueError("Checkpoint corrupto")
        return payload["state"]

def exact_sha256(text: str) -> str:
    if not isinstance(text,str):
        raise TypeError("Fragmento inválido")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
