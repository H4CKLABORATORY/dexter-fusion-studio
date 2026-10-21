#!/usr/bin/env python3
"""DEXTER shared local context for LU Code. Does not read or export LU chat databases.

Run: python tools/lu-memory/sync_context.py --parent "C:\Users\YOU\Projects"
or:  python tools/lu-memory/sync_context.py --repo "C:\path\repo" [--repo ...]
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

PRIVATE_DIR = ".dexter-local"
RULES = """# DEXTER LU Code - continuidad entre sesiones
Al iniciar: lee este archivo, AGENTS.md/README.md si existen y
.dexter-local/SHARED_CONTEXT.md y .dexter-local/LAST_SESSION.md.
Comprueba git status/HEAD y las pruebas antes de editar. Evita repetir tareas ya
verificadas. Al terminar o al agotar contexto, actualiza
.dexter-local/LAST_SESSION.md con objetivo, cambios, rama, pruebas REALES,
bloqueos y accion siguiente. No escribas secretos ni exportaciones privadas en
GitHub; .dexter-local es informacion solo del equipo local. Trabaja en ramas y
no declares despliegues o pruebas que no se verificaron.
"""
MASTER = """# DEXTER - contexto compartido LOCAL para LU
Este archivo es PRIVADO y puede editarse para agregar prioridades, decisiones y
un resumen autorizado de las conversaciones. No se publica en GitHub.
Proyectos conocidos (verificar el estado real en cada repositorio):
- DEXTER Fusion Studio: editor Qt/Python y FFmpeg.
- 1UP Anime: catalogo web y experiencia de anime.
- DEXTER AI Web: interfaz web y backend de IA.
- DEXTER AI STUDIO: plataforma Cloudflare + pagos + generacion (plan/no asumir deploy).
- DEXTER HERMES AI STUDIO: orquestacion/autonomia local (no asumir instalada).
Nunca incorporar claves API, contrasenas ni tokens de Stripe/Higgsfield.
"""
SESSION = """# Ultima sesion verificable

Fecha:
Objetivo:
Rama y commit:
Archivos cambiados:
Pruebas ejecutadas y resultados:
Pendientes/bloqueos:
Siguiente accion exacta:
"""

def is_repo(folder: Path) -> bool:
    return folder.is_dir() and ((folder / ".git").exists() or (folder / ".lurules").is_file())

def discover(explicit: list[str], parents: list[str]) -> list[Path]:
    found: dict[str, Path] = {}
    for name in explicit:
        folder = Path(name).expanduser().resolve()
        if not is_repo(folder):
            raise ValueError(f"No es raiz de repositorio/carpeta LU: {folder}")
        found[str(folder).lower()] = folder
    for name in parents:
        parent = Path(name).expanduser().resolve()
        if not parent.is_dir():
            raise ValueError(f"No existe la carpeta de proyectos: {parent}")
        for candidate in [parent, *parent.iterdir()]:
            if is_repo(candidate):
                found[str(candidate).lower()] = candidate
    return sorted(found.values(), key=lambda p: str(p).lower())

def write_if_absent(path: Path, content: str) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

def ignore_private(root: Path) -> None:
    # Does not modify tracked .gitignore. Handles ordinary clones; repositories
    # with git worktree .git files need their existing .gitignore to exclude it.
    git_dir = root / ".git"
    if git_dir.is_dir():
        info = git_dir / "info" / "exclude"
        info.parent.mkdir(parents=True, exist_ok=True)
        old = info.read_text(encoding="utf-8") if info.exists() else ""
        if PRIVATE_DIR + "/" not in old.splitlines():
            info.write_text(old.rstrip("\n") + "\n" + PRIVATE_DIR + "/\n", encoding="utf-8")

def build_shared(master: str, repos: list[Path]) -> str:
    blocks = ["# Contexto compartido entre proyectos de LU",
              "Generado LOCALMENTE. No subir a GitHub. Fuente principal: MASTER_CONTEXT.md.",
              "", master.strip(), "", "## Ultimos estados locales por proyecto"]
    for root in repos:
        session = root / PRIVATE_DIR / "LAST_SESSION.md"
        if session.is_file():
            detail = session.read_text(encoding="utf-8", errors="replace").strip()[:4000]
        else:
            detail = "Sin checkpoint local previo."
        blocks.extend(["", "### " + root.name, detail])
    return "\n".join(blocks) + "\n"

def sync(repos: list[Path], memory_home: Path) -> None:
    if not repos:
        raise ValueError("No se encontraron repositorios; usa --repo o --parent.")
    memory_home.mkdir(parents=True, exist_ok=True)
    master_path = memory_home / "MASTER_CONTEXT.md"
    write_if_absent(master_path, MASTER)
    for root in repos:
        local = root / PRIVATE_DIR
        local.mkdir(exist_ok=True)
        write_if_absent(local / "LAST_SESSION.md", SESSION)
        write_if_absent(root / ".lurules", RULES)
        ignore_private(root)
    shared = build_shared(master_path.read_text(encoding="utf-8"), repos)
    for root in repos:
        (root / PRIVATE_DIR / "SHARED_CONTEXT.md").write_text(shared, encoding="utf-8")
        print(f"OK {root} - .lurules + contexto compartido + checkpoint local")
    print(f"Memoria maestra privada: {master_path}")
    print("IMPORTANTE: ejecuta de nuevo este script al cambiar checkpoints para propagarlos.")

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", action="append", default=[], help="Raiz de un proyecto; repetible")
    parser.add_argument("--parent", action="append", default=[], help="Carpeta con varios repos, profundidad 1")
    parser.add_argument("--memory-home", default=os.path.join(
        os.environ.get("LOCALAPPDATA", str(Path.home() / ".local" / "share")), "DEXTER-MEMORY"))
    args = parser.parse_args()
    try:
        sync(discover(args.repo, args.parent), Path(args.memory_home).expanduser().resolve())
    except ValueError as exc:
        parser.error(str(exc))

if __name__ == "__main__":
    main()
