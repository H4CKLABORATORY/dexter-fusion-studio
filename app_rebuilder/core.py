"""Safe, read-only binary inventory; no execution or unpacking."""
from pathlib import Path
import hashlib

def inspect_file(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError("Se requiere un archivo existente")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        header = stream.read(16)
        digest.update(header)
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    kind = "unknown"
    if header.startswith(b"MZ"):
        kind = "PE (Windows, probable)"
    elif header.startswith(b"\\x7fELF"):
        kind = "ELF"
    elif header[:4] in (bytes.fromhex(x) for x in ("feedface", "feedfacf", "cefaedfe", "cffaedfe", "cafebabe", "bebafeca")):
        kind = "Mach-O/Fat"
    elif header.startswith(b"PK\\x03\\x04"):
        kind = "ZIP/APK (requiere inspección adicional)"
    return {"name": path.name, "size_bytes": path.stat().st_size, "sha256": digest.hexdigest(), "format": kind}
