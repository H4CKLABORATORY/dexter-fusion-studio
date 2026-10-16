"""Importaciones privadas y etiquetas de memes; preserva originales y deduplica por hash."""
import hashlib, shutil, json
from pathlib import Path
from .project import safe_write,read_json
EXTS={'.txt','.md','.srt'}

def import_scripts(workspace,source,max_files=300):
    workspace=Path(workspace).expanduser().resolve();source=Path(source).expanduser().resolve()
    if not source.is_dir():raise ValueError('No existe la carpeta')
    dest=workspace/'scripts';dest.mkdir(parents=True,exist_ok=True)
    path=workspace/'scripts-index.json'; items=read_json(path,{'entries':[]})
    known={x['hash'] for x in items['entries']}
    files=[p for p in source.rglob('*') if p.is_file() and p.suffix.lower() in EXTS]
    if len(files)>max_files:raise ValueError('Lote demasiado grande: máximo 300 archivos')
    added=[];dupes=0
    for file in files:
        if file.stat().st_size>2_000_000:continue
        raw=file.read_bytes()
        try:raw.decode('utf-8-sig')
        except UnicodeError:continue
        key=hashlib.sha256(raw).hexdigest()
        if key in known:dupes+=1;continue
        output=dest/f'{key[:12]}-{file.name}'
        shutil.copy2(file,output)
        items['entries'].append({'title':file.stem,'hash':key,'path':str(output),'words':len(raw.decode('utf-8-sig').split()),'complete':True})
        known.add(key);added.append(file.stem)
    safe_write(path,items)
    return {'added':added,'duplicates':dupes,'total':len(items['entries'])}

def add_meme(workspace,file,tags,license='owned'):
    file=Path(file).expanduser().resolve()
    if not file.is_file() or file.suffix.lower() not in ('.png','.jpg','.jpeg','.webp'):raise ValueError('Solo imágenes de meme')
    if license not in ('owned','licensed','permitted'):raise ValueError('Usar únicamente recursos propios/autorizados')
    dst=Path(workspace).expanduser().resolve()/'memes';dst.mkdir(parents=True,exist_ok=True)
    h=hashlib.sha256(file.read_bytes()).hexdigest()[:12]
    output=dst/f'{h}{file.suffix.lower()}'
    if not output.exists():shutil.copy2(file,output)
    row={'path':str(output),'tags':[x.strip().lower() for x in tags.split(',') if x.strip()], 'license':license,'approved':True}
    records=read_json(dst/'index.json',{'assets':[]})
    if row['path'] not in [x['path'] for x in records['assets']]:records['assets'].append(row)
    safe_write(dst/'index.json',records)
    return row
