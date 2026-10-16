"""Gestión de proyectos sin alterar videos de origen ni usar la nube."""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
import re
import uuid

VIDEO_EXT = {'.mp4', '.mov', '.mkv', '.webm', '.avi'}
PROFILES = {
    'freefire_story': {'name':'Free Fire: historias/novela','keywords':['free fire','freefire','isla social','chacalita','interesada','botsito','infieles','novela'],'format':'youtube','duration':0,'effects':'cinematic','kind':'long'},
    'freefire_short': {'name':'Free Fire: Shorts y TikTok','keywords':['free fire','freefire','pvp','clip','short','tiktok','manco','toxico','botsito'],'format':'tiktok','duration':30,'effects':'hype','kind':'short'},
    'tutorial': {'name':'Tutorial','keywords':['tutorial','como hacer','guia','paso a paso','instalar'],'format':'youtube','duration':0,'effects':'clean','kind':'long'},
    'reaction': {'name':'Reacción y memes','keywords':['reaccion','reaction','reaccionando','humor','memes'],'format':'tiktok','duration':45,'effects':'hype','kind':'short'},
    'vlog': {'name':'Vlog','keywords':['vlog','viaje','rutina','mi dia'],'format':'youtube','duration':0,'effects':'cinematic','kind':'long'},
}
PERSONAL_STYLE = {
    'name':'Dexter FF', 'lang':'es-LATAM',
    'voice':'Conservar audio/voz de grabación propia; narración externa solo autorizada',
    'vocabulary':['bro','cracks','vato','chacalito','chacalita','botsito','manco','veterano de papel'],
    'avoid':['booyah','headshot','squad','coño','nah','watsito','huatsito'],
    'story':['Gancho natural','contexto','conflicto','reacción','giro','remate'],
    'long':'Intros más largas cuando el formato lo pide; diálogo espontáneo; no cortar chistes por silencio sin revisión',
    'short':'Gancho rápido, reacción, textos sincronizados, memes pertinentes, remate',
    'safe_area':'Mantener subtítulos y overlays en zona segura de móvil',
    'source':'Preferencias previas del usuario; NO es una transcripción completa de videos o guiones.'
}
KNOWN_SCRIPT_TITLES = [
 'Cazando interesadas','Buscando interesadas 2','Pareja de infieles',
 'FARMEANDO AURA EN ISLA SOCIAL','Cuando el tío Dexter termina un PVP humillando tóxicos',
 'Sacando los nuevos cuernitos insanos','Vayan a seguirme'
]

def safe_slug(name: str) -> str:
    v = re.sub(r'[^a-z0-9]+','-',name.lower().strip()).strip('-')[:65]
    return v or 'proyecto'

def safe_write(path:Path, obj:dict):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding='utf-8')
    tmp.replace(path)

def read_json(path, default=None):
    p=Path(path)
    if not p.exists(): return default if default is not None else {}
    return json.loads(p.read_text(encoding='utf-8'))

def detect_profile(name:str, script:str='', filename:str=''):
    """Inferencia conservadora basada en texto; NO análisis semántico audiovisual."""
    text=(name+' '+filename+' '+script[:1400]).lower()
    scores=[]
    for id,profile in PROFILES.items():
        matched=[w for w in profile['keywords'] if w in text]
        scores.append((len(matched),id,matched))
    scores.sort(reverse=True)
    leading=scores[0]
    runner=scores[1][0]
    if leading[0]>=2 and (leading[0]-runner)>=2:
        return {'status':'recognized','profile':leading[1], 'evidence':leading[2]}
    return {'status':'needs_input','profile':None,'suggestions':[s[1] for s in scores[:3] if s[0]], 'questions':['¿Qué tipo de video haremos?','¿Para qué es el video?','¿YouTube, Shorts o TikTok?','¿Qué ritmo o método de edición quieres?']}

def create_project(workspace:str,name:str,source:str,profile:str='auto',purpose:str='entretenimiento',platform:str|None=None):
    media=Path(source).expanduser().resolve()
    if not media.is_file() or media.suffix.lower() not in VIDEO_EXT: raise ValueError('Selecciona un video local válido')
    workspace=Path(workspace).expanduser().resolve()
    folder=workspace / f'{safe_slug(name)}-{uuid.uuid4().hex[:6]}'
    folder.mkdir(parents=True,exist_ok=False)
    for sub in ('output','scripts','memes','references','previews'):(folder/sub).mkdir()
    script=''
    result=detect_profile(name,script,media.stem)
    if profile=='auto':
        if not result['profile']: raise ValueError('Falta determinar tipo de video: elige un perfil o crea uno.')
        profile=result['profile']
    if profile not in PROFILES: raise ValueError('Perfil desconocido')
    item={
        'schema':1, 'name':name,'source':str(media), 'source_is_external':True,
        'created_at':datetime.now(timezone.utc).isoformat(),'profile':profile,
        'platform':platform or PROFILES[profile]['format'],'purpose':purpose,
        'guion':None, 'subtitle_file':None,'watermark_file':None,
        'meme_assets':[], 'effects':PROFILES[profile]['effects'],
        'silence_cut':False, 'minimum_clip':1.1,'maximum_length':PROFILES[profile]['duration'],
        'cut_style':'hard', 'clip_ranges':[], 'events':[],
        'review_required':True,'status':'prepared'
    }
    safe_write(folder/'project.json',item)
    (folder/'GUIA_DE_EDICION.md').write_text('# '+name+'\n\nGancho:\n\nEscenas:\n\nMemes:\n\nNarración:\n\nRevisión final:\n',encoding='utf-8')
    return folder,item

def seed_personal_knowledge(workspace):
    workspace=Path(workspace).expanduser().resolve()
    workspace.mkdir(parents=True,exist_ok=True)
    styles=workspace/'personal_style.json'
    titles=workspace/'known_script_titles.json'
    if not styles.exists(): safe_write(styles, PERSONAL_STYLE)
    if not titles.exists(): safe_write(titles, {'titles_only':KNOWN_SCRIPT_TITLES,'full_texts_imported':0,'warning':'Los títulos recordados no contienen el texto de los guiones.'})
    return styles,titles
