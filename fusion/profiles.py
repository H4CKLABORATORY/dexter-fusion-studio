"""Perfiles locales con bloqueo por contrasena para Dexter Fusion Studio.

SOLO LOCAL: no hay cuentas en la nube ni red. Cada persona que usa la
misma maquina tiene su propio perfil, con su lista de proyectos y sus
ajustes guardados en una carpeta propia bajo el directorio de la app
(Documentos/DexterFusionStudio en Windows, o $DEXTER_FUSION_HOME en
pruebas). La contrasena NUNCA se guarda en texto claro: solo su hash.

Hash: bcrypt cuando la libreria esta instalada (recomendado en Windows,
``pip install bcrypt``), si no PBKDF2-HMAC-SHA256 de la libreria
estandar (600.000 iteraciones, sal aleatoria). El hash guardado indica
su propio algoritmo, asi que verificar funciona en cualquier maquina.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .project import read_json, safe_slug, safe_write

try:  # bcrypt es opcional: si no esta, se usa PBKDF2 (stdlib).
    import bcrypt as _bcrypt
except ImportError:  # pragma: no cover - depende del entorno
    _bcrypt = None

GUEST_NAME = 'Invitado'
GUEST_SLUG = 'invitado'
PROFILE_SCHEMA = 1
MIN_PASSWORD_LENGTH = 4
_PBKDF2_ITERATIONS = 600_000
_PBKDF2_PREFIX = 'pbkdf2_sha256'

DEFAULT_SETTINGS = {
    'language': 'es',
    'volume': 0.55,
    'default_profile': 'freefire_short',
    'default_format': 'tiktok',
}


def hasher_name() -> str:
    """Algoritmo que se usara para nuevos hashes en esta maquina."""
    return 'bcrypt' if _bcrypt is not None else 'pbkdf2_sha256'


def hash_password(password: str) -> str:
    """Devuelve el hash de una contrasena (nunca la contrasena misma)."""
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f'La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.')
    raw = password.encode('utf-8')
    if _bcrypt is not None:
        return _bcrypt.hashpw(raw, _bcrypt.gensalt(rounds=12)).decode('ascii')
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac('sha256', raw, salt, _PBKDF2_ITERATIONS)
    b64 = lambda b: base64.b64encode(b).decode('ascii')
    return f'{_PBKDF2_PREFIX}${_PBKDF2_ITERATIONS}${b64(salt)}${b64(dk)}'


def verify_password(password: str, stored: str | None) -> bool:
    """True si la contrasena coincide con el hash guardado.

    Un perfil sin hash (stored None) no tiene bloqueo: cualquier
    contrasena vacia/ausente lo abre; una contrasena no vacia no.
    """
    if stored is None:
        return not password
    if not isinstance(password, str) or not password:
        return False
    try:
        if stored.startswith(('$2a$', '$2b$', '$2y$')):
            if _bcrypt is None:
                return False
            return _bcrypt.checkpw(password.encode('utf-8'),
                                   stored.encode('ascii'))
        if stored.startswith(_PBKDF2_PREFIX + '$'):
            _, iterations, salt_b64, dk_b64 = stored.split('$')
            salt = base64.b64decode(salt_b64)
            expected = base64.b64decode(dk_b64)
            dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                                     salt, int(iterations))
            return hmac.compare_digest(dk, expected)
    except (ValueError, TypeError):
        return False
    return False


def default_app_root() -> Path:
    """Raiz de datos de la app (perfiles, proyectos y ajustes)."""
    override = os.environ.get('DEXTER_FUSION_HOME')
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / 'Documents' / 'DexterFusionStudio'


@dataclass
class Profile:
    """Un perfil local: nombre visible, carpeta propia y bloqueo opcional."""
    name: str
    slug: str
    created_at: str
    password_hash: str | None = None
    settings: dict = field(default_factory=dict)

    @property
    def has_password(self) -> bool:
        return self.password_hash is not None

    def to_public_dict(self) -> dict:
        """Datos seguros para mostrar: NUNCA incluyen el hash."""
        return {'name': self.name, 'slug': self.slug,
                'created_at': self.created_at,
                'has_password': self.has_password}


class ProfileManager:
    """Crea, abre, cambia y elimina perfiles locales."""

    def __init__(self, app_root: str | Path | None = None):
        self.app_root = Path(app_root).expanduser().resolve() \
            if app_root is not None else default_app_root()
        self.profiles_dir = self.app_root / 'profiles'
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_guest()

    # -- rutas ---------------------------------------------------------
    def profile_dir(self, slug: str) -> Path:
        return self.profiles_dir / safe_slug(slug)

    def workspace(self, slug: str) -> Path:
        """Carpeta de proyectos de un perfil (se crea si no existe)."""
        path = self.profile_dir(slug) / 'projects'
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _profile_file(self, slug: str) -> Path:
        return self.profile_dir(slug) / 'profile.json'

    def _settings_file(self, slug: str) -> Path:
        return self.profile_dir(slug) / 'settings.json'

    # -- lectura -------------------------------------------------------
    def _load(self, slug: str) -> Profile:
        data = read_json(self._profile_file(slug), None)
        if not data:
            raise KeyError(f'No existe el perfil: {slug}')
        settings = read_json(self._settings_file(slug), {})
        return Profile(name=data['name'], slug=data['slug'],
                       created_at=data.get('created_at', ''),
                       password_hash=data.get('password_hash'),
                       settings=settings)

    def _save(self, profile: Profile) -> None:
        folder = self.profile_dir(profile.slug)
        folder.mkdir(parents=True, exist_ok=True)
        safe_write(self._profile_file(profile.slug), {
            'schema': PROFILE_SCHEMA, 'name': profile.name,
            'slug': profile.slug, 'created_at': profile.created_at,
            'password_hash': profile.password_hash})
        safe_write(self._settings_file(profile.slug),
                   dict(profile.settings))

    def _ensure_guest(self) -> Profile:
        if not self._profile_file(GUEST_SLUG).exists():
            guest = Profile(name=GUEST_NAME, slug=GUEST_SLUG,
                            created_at=datetime.now(timezone.utc).isoformat(),
                            password_hash=None,
                            settings=dict(DEFAULT_SETTINGS))
            self._save(guest)
            return guest
        return self._load(GUEST_SLUG)

    def list_profiles(self) -> list[Profile]:
        profiles = []
        for folder in sorted(self.profiles_dir.iterdir()):
            if folder.is_dir() and self._profile_file(folder.name).exists():
                profiles.append(self._load(folder.name))
        return profiles

    def get_profile(self, slug: str) -> Profile:
        return self._load(safe_slug(slug))

    def find_by_name(self, name: str) -> Profile | None:
        wanted = name.strip().lower()
        for profile in self.list_profiles():
            if profile.name.strip().lower() == wanted:
                return profile
        return None

    # -- creacion / borrado --------------------------------------------
    def create_profile(self, name: str, password: str | None = None) -> Profile:
        name = (name or '').strip()
        if not name:
            raise ValueError('El perfil necesita un nombre.')
        if len(name) > 50:
            raise ValueError('El nombre del perfil es demasiado largo (máx. 50).')
        slug = safe_slug(name)
        if self.find_by_name(name) is not None or \
                self._profile_file(slug).exists():
            raise ValueError(f'Ya existe un perfil llamado "{name}".')
        profile = Profile(
            name=name, slug=slug,
            created_at=datetime.now(timezone.utc).isoformat(),
            password_hash=hash_password(password) if password else None,
            settings=dict(DEFAULT_SETTINGS))
        self._save(profile)
        self.workspace(slug)
        return profile

    def delete_profile(self, slug: str, password: str | None = None) -> str:
        """Elimina un perfil y TODOS sus proyectos. Devuelve su nombre."""
        profile = self._load(safe_slug(slug))
        if profile.has_password and not verify_password(password or '', profile.password_hash):
            raise ValueError('Contraseña incorrecta: no se puede eliminar el perfil.')
        if len(self.list_profiles()) <= 1:
            raise ValueError('No se puede eliminar el último perfil.')
        shutil.rmtree(self.profile_dir(profile.slug))
        return profile.name

    # -- bloqueo / desbloqueo -------------------------------------------
    def unlock(self, slug: str, password: str | None = None) -> Profile:
        """Abre un perfil: sin contrasena si no tiene bloqueo, o con la
        correcta. Con contrasena incorrecta no hay entrada (ValueError)."""
        profile = self._load(safe_slug(slug))
        if profile.has_password:
            if not verify_password(password or '', profile.password_hash):
                raise ValueError('Contraseña incorrecta.')
        return profile

    def change_password(self, slug: str, current_password: str | None,
                        new_password: str | None) -> Profile:
        """Cambia la contrasena (pide la actual si hay una). Con
        new_password None o vacio se quita el bloqueo."""
        profile = self._load(safe_slug(slug))
        if profile.has_password and not verify_password(
                current_password or '', profile.password_hash):
            raise ValueError('Contraseña actual incorrecta.')
        profile.password_hash = hash_password(new_password) \
            if new_password else None
        self._save(profile)
        return profile

    # -- ajustes y proyectos por perfil ----------------------------------
    def get_settings(self, slug: str) -> dict:
        return dict(self._load(safe_slug(slug)).settings)

    def update_settings(self, slug: str, patch: dict) -> dict:
        if not isinstance(patch, dict):
            raise ValueError('Los ajustes deben ser un diccionario.')
        profile = self._load(safe_slug(slug))
        profile.settings.update(patch)
        self._save(profile)
        return dict(profile.settings)

    def list_projects(self, slug: str) -> list[dict]:
        """Proyectos del perfil: carpetas con project.json, ordenadas."""
        self._load(safe_slug(slug))  # el perfil debe existir
        found = []
        for folder in sorted(self.workspace(slug).iterdir()):
            if folder.is_dir() and (folder / 'project.json').is_file():
                data = read_json(folder / 'project.json', {})
                found.append({'name': data.get('name', folder.name),
                              'path': str(folder)})
        return found

    # -- perfil activo ----------------------------------------------------
    def get_active_slug(self) -> str:
        data = read_json(self.app_root / 'active.json', {})
        slug = data.get('slug') if isinstance(data, dict) else None
        if slug and self._profile_file(slug).exists():
            return slug
        return GUEST_SLUG

    def set_active_slug(self, slug: str) -> None:
        self._load(safe_slug(slug))  # el perfil debe existir
        safe_write(self.app_root / 'active.json', {'slug': safe_slug(slug)})
