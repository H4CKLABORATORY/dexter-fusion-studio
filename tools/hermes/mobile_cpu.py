"""Pinned CPU fallback with vendor SHA-256 verification. Linux x86_64."""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import platform
import secrets
import shutil
import tarfile
import urllib.request

LLAMA_URL = 'https://github.com/ggml-org/llama.cpp/releases/download/b11935/llama-b11935-bin-ubuntu-x64.tar.gz'
LLAMA_SHA = '292803ab33750b8fee028df2b988b146f1f96d75ee7570c86f2eff01479bff55'
MODEL_URL = 'https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/f86cb2c1fa58255f8052cc32aeede1b7482d4361/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf'
MODEL_SHA = 'cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046'
MODEL_BYTES = 1117320768

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()

def download(url, dest, expected, limit):
    if dest.is_symlink(): raise ValueError('Destino no puede ser un enlace')
    if dest.exists() and sha256(dest) == expected: return
    tmp = dest.with_suffix('.part-' + secrets.token_hex(4))
    try:
        with urllib.request.urlopen(url, timeout=60) as response, tmp.open('xb') as f:
            size = 0
            while block := response.read(1024 * 1024):
                size += len(block)
                if size > limit: raise ValueError('Descarga excede el tamaño permitido')
                f.write(block)
        if sha256(tmp) != expected: raise ValueError('SHA-256 incorrecto; descarga rechazada')
        os.replace(tmp, dest)
    finally: tmp.unlink(missing_ok=True)

def extract(archive, dest):
    dest.mkdir(parents=True, mode=0o700, exist_ok=True)
    with tarfile.open(archive, 'r:gz') as tar:
        for entry in tar.getmembers():
            target = (dest / entry.name).resolve()
            linked = (target.parent / entry.linkname).resolve() if entry.issym() else (dest / entry.linkname).resolve() if entry.islnk() else target
            for candidate in (target, linked):
                if candidate != dest.resolve() and dest.resolve() not in candidate.parents:
                    raise ValueError('Archivo o enlace fuera del destino')
            if entry.isdev() or entry.isfifo(): raise ValueError('Archivo especial rechazado')
        tar.extractall(dest, filter='data')

def install(store):
    if platform.system() != 'Linux' or platform.machine() not in {'x86_64', 'AMD64'}:
        raise ValueError('Respaldo CPU verificado solo en Linux x86_64')
    dest = store / 'cpu'; dest.mkdir(mode=0o700, exist_ok=True)
    if not (dest / 'model.gguf').exists() and shutil.disk_usage(dest).free < 1700000000:
        raise ValueError('Se necesitan 1.7 GB libres')
    download(LLAMA_URL, dest / 'llama.tar.gz', LLAMA_SHA, 30000000)
    download(MODEL_URL, dest / 'model.gguf', MODEL_SHA, MODEL_BYTES)
    extract(dest / 'llama.tar.gz', dest / 'llama')
    from mobile import save
    result = {'llama_version': 'b11935', 'llama_sha256': LLAMA_SHA, 'model_sha256': MODEL_SHA,
              'model': 'Qwen2.5-Coder-1.5B-Instruct Q4_K_M', 'license': 'Apache-2.0', 'model_bytes': MODEL_BYTES}
    save(dest / 'verified.json', result)
    return result

def server_command(store, api_key):
    dest = store / 'cpu'
    if not (dest / 'verified.json').exists() or not (dest / 'model.gguf').is_file():
        raise ValueError('Ejecuta mobile.py install-cpu')
    servers = list((dest / 'llama').rglob('llama-server'))
    if len(servers) != 1: raise ValueError('Instalación CPU incompleta')
    keyfile = dest / 'api-key'
    if keyfile.is_symlink(): raise ValueError('Archivo de clave inválido')
    fd = os.open(keyfile, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f: f.write(api_key + '\n')
    keyfile.chmod(0o600)
    return [str(servers[0]), '--model', str(dest / 'model.gguf'), '--host', '127.0.0.1', '--port', '8081',
        '--ctx-size', '16384', '--threads', '2', '--parallel', '1', '--n-gpu-layers', '0', '--jinja',
        '--alias', 'qwen2.5-coder-1.5b', '--api-key-file', str(keyfile), '--cors-origins', 'http://127.0.0.1']
