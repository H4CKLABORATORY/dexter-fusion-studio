"""Integraciones verificables. Evita afirmar que los tres programas están fusionados físicamente."""
import json, os, shutil, subprocess
from pathlib import Path
from .project import safe_write
from .rea_bridge import find_rea

REFERENCE={
 'concat':{'repository':'https://github.com/jub0t/Concat','license':'AGPL-3.0-or-later','status':'API JSON-RPC publicada; hay que configurar transporte y revisar versión instalada'},
 'filmcraft':{'repository':'https://github.com/storytold/filmcraft','license':'MIT OR Apache-2.0','status':'CLI + MCP documentado'},
 'effectcraft':{'repository':'https://github.com/storytold/effectcraft','license':'MIT OR Apache-2.0','status':'CLI + MCP documentado'},
 'opencreator':{'repository':'https://github.com/krillinai/OpenCreator','license':'Apache-2.0','status':'CLI KrillinAI opcional'},
}

def defaults():
    return {
        'rea_cli': '',
        'concat_exe':r'C:\Program Files\Concat\Concat.exe',
        'filmcraft_cli':r'C:\Program Files\FilmCraft\filmcraft-cli.exe',
        'effectcraft_cli':r'C:\Program Files\EffectCraft\effectcraft-cli.exe',
        'filmcraft_exe':r'C:\Program Files\FilmCraft\filmcraft.exe',
        'effectcraft_exe':r'C:\Program Files\EffectCraft\effectcraft.exe',
    }

def scan(config=None):
    config={**defaults(),**(config or {})}
    out={}
    for name,key in [('Concat','concat_exe'),('FilmCraft CLI','filmcraft_cli'),('EffectCraft CLI','effectcraft_cli')]:
        path=Path(config[key])
        out[name]={'found':path.is_file(), 'path':str(path), 'configured':True}
    for binary in ('ffmpeg','ffprobe','python'):
        out[binary]={'found':bool(shutil.which(binary)),'path':shutil.which(binary)}
    try:
        rea = find_rea(config.get('rea_cli') or None)
    except FileNotFoundError:
        out['REA'] = {'found': False, 'path': None}
    else:
        out['REA'] = {'found': True, 'path': rea}
    return out

def export_mcp_client_config(destination,config):
    """Genera configuración válida sin inventar herramientas ni instalar nada."""
    config={**defaults(),**(config or {})}
    mcp={}
    for key,name,args in [('filmcraft_cli','filmcraft',['mcp']),('effectcraft_cli','effectcraft',['mcp'])]:
        path=Path(config[key]).expanduser()
        if path.is_file():mcp[name]={'command':str(path.resolve()),'args':args}
    try:
        rea = find_rea(config.get('rea_cli') or None)
    except FileNotFoundError:
        pass
    else:
        mcp['rea'] = {'command': rea, 'args': ['mcp']}
    safe_write(Path(destination),{'mcpServers':mcp})
    return list(mcp)

def launch_app(executable):
    path=Path(executable).expanduser().resolve()
    if not path.is_file() or path.suffix.lower()!='.exe':raise ValueError('No se encontró un ejecutable Windows válido')
    subprocess.Popen([str(path)],close_fds=True)
    return path

def render_filmcraft_project(executable,project_file,output_file):
    """Exportador FilmCraft headless, interfaz oficial documentada.

    Requiere que el proyecto .fcproj ya exista y FilmCraft esté instalado.
    """
    exe=Path(executable).expanduser().resolve()
    project=Path(project_file).expanduser().resolve()
    target=Path(output_file).expanduser().resolve()
    if not exe.is_file():raise FileNotFoundError('Instala FilmCraft CLI o selecciona su ejecutable')
    if not project.is_file() or project.suffix.lower()!='.fcproj':raise ValueError('Selecciona un proyecto .fcproj')
    if target.suffix.lower() not in ('.mp4','.mov'):raise ValueError('Formato de exportación no admitido en este flujo')
    if target.exists():raise FileExistsError('No se sobrescribe una exportación existente')
    target.parent.mkdir(parents=True,exist_ok=True)
    result=subprocess.run([str(exe),'--project',str(project),'export',str(target)],capture_output=True,text=True,timeout=3600)
    if result.returncode or not target.is_file():raise RuntimeError((result.stderr or result.stdout)[-2000:])
    return target

def render_effectcraft_project(executable,project_file,output_file,comp='Main'):
    """Exportador EffectCraft documentado: render --comp X --out Y project.ecproj."""
    exe=Path(executable).expanduser().resolve()
    project=Path(project_file).expanduser().resolve()
    target=Path(output_file).expanduser().resolve()
    if not exe.is_file():raise FileNotFoundError('Instala EffectCraft CLI o selecciona su ejecutable')
    if not project.is_file() or project.suffix.lower()!='.ecproj':raise ValueError('Selecciona un proyecto .ecproj')
    if target.suffix.lower() not in ('.mp4','.mov','.webm'):raise ValueError('Formato no admitido en este flujo')
    if target.exists():raise FileExistsError('No se sobrescribe una exportación existente')
    target.parent.mkdir(parents=True,exist_ok=True)
    result=subprocess.run([str(exe),'render','--comp',comp,'--out',str(target),str(project)],capture_output=True,text=True,timeout=3600)
    if result.returncode or not target.is_file():raise RuntimeError((result.stderr or result.stdout)[-2000:])
    return target
