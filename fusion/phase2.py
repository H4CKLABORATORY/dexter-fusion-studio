"""Etapa 2: editor cronológico revisable y sugerencias de highlights.

Señales: cortes detectados, silencios y palabras elegidas en un SRT.
No clasifica emociones, kills, chistes ni personajes con un modelo multimodal.
"""
from __future__ import annotations
from pathlib import Path
import json
import math
import re
from .media import probe, scene_changes, silence_ranges, keep_ranges, required, run
from .project import read_json, safe_write
from .engine import read_srt, map_srt, suggest_memes, EFFECTS

HOOKS = ('bro', 'manco', 'botsito', 'interesada', 'sorpresa', 'traición',
         'chacalito', 'chacalita', 'qué', 'no', 'jajaja', 'espera', 'mira')


def score_windows(duration, scene_times, silent_ranges, captions, *, window=12, step=4):
    """Ordena propuestas con razones auditables; NO recomienda viralidad."""
    if duration <= 0 or window <= 0 or step <= 0:
        return []
    candidates = []
    start = 0.0
    while start < duration:
        end = min(duration, start + window)
        if end - start < min(2.0, duration):
            break
        hits = [t for t in scene_times if start <= t < end]
        silent = sum(max(0, min(end, b) - max(start, a)) for a, b in silent_ranges)
        silent_ratio = min(1.0, silent / max(.1, end - start))
        words = [sub['text'] for sub in captions if start <= sub['start'] < end]
        keywords = sorted({keyword for keyword in HOOKS
                           if any(re.search(r'(?<!\w)'+re.escape(keyword)+r'(?!\w)',text.casefold()) for text in words)})
        # Estímulo visual y frases de gancho son señales, no comprensión del juego.
        score = round(max(0, 1.3*min(4, len(hits)) + 2.1*min(3, len(keywords))
                           + 0.45*min(3, len(words)) - 7.0*silent_ratio), 3)
        candidates.append({'start': round(start, 3), 'end': round(end, 3),
                           'score': score, 'scene_count': len(hits),
                           'silence_ratio': round(silent_ratio, 3),
                           'keyword_evidence': keywords, 'subtitles': len(words),
                           'reason': 'Heurística: cambios visuales, texto y proporción de silencios'})
        start += step
    return sorted(candidates, key=lambda c: (-c['score'], c['start']))


def select_nonoverlap(candidates, *, limit=5, padding=0.30):
    selected=[]
    for c in candidates:
        if any(not (c['end'] + padding <= other['start'] or
                    other['end'] + padding <= c['start']) for other in selected):
            continue
        selected.append(c)
        if len(selected)>=limit:
            break
    return sorted(selected, key=lambda c:c['start'])


def suggest_effect_for_caption(text, fallback='clean'):
    """Preset sugerido por palabras comprobables del SRT; NO detecta emoción real."""
    lower=text.casefold()
    rules=[
        (('traición','infiel','triste','llorando','engaño'),'monochrome'),
        (('sorpresa','wtf','¡no!','qué pasó','que paso'),'glitch'),
        (('recuerdo','antes','veterano','antiguo'),'vhs'),
        (('pvp','batalla','disparos','pelea','ganamos','botsito'),'hype'),
    ]
    for terms,preset in rules:
        if any(term in lower for term in terms):
            return preset, 'Coincidencia de frase en subtítulos: '+', '.join(x for x in terms if x in lower)
    return fallback, 'Sin palabras clave específicas; mantiene estilo del proyecto.'


def build_timeline(folder, *, scan_seconds=120, select_highlights=False, limit=5,
                   window=12, automatic_silence=False, automatic_effects=True, overwrite=False):
    folder=Path(folder).resolve()
    filename=folder/'timeline-v2.json'
    if filename.exists() and not overwrite:
        raise FileExistsError('El timeline ya existe; edítalo o activa sobrescribir explícitamente.')
    project=read_json(folder/'project.json')
    src=Path(project['source']).expanduser().resolve()
    info=probe(src)
    if info['duration']<=0:
        raise ValueError('El video carece de duración verificable.')
    cuts=scene_changes(src, max_seconds=min(float(scan_seconds),info['duration']))
    silences=silence_ranges(src) if info['audio'] else []
    captions=read_srt(project['subtitle_file']) if project.get('subtitle_file') and Path(project['subtitle_file']).is_file() else []
    candidates=score_windows(info['duration'],cuts,silences,captions,window=window)
    if select_highlights:
        chosen=select_nonoverlap(candidates,limit=limit)
        intervals=[[x['start'],x['end']] for x in chosen]
    else:
        # No eliminar pausas de novela sin que el usuario lo active.
        intervals=keep_ranges(info['duration'], silences, min_keep=float(project.get('minimum_clip',1.1))) if automatic_silence else [[0,info['duration']]]
    if not intervals:
        intervals=[[0, info['duration']]]
    clip_effect=project.get('effects','clean')
    annotated=[]
    for i,(a,b) in enumerate(intervals):
        within=' '.join(row['text'] for row in captions if a<=row['start']<b)
        proposed,reason=suggest_effect_for_caption(within, clip_effect) if automatic_effects else (clip_effect,'Efecto elegido en proyecto')
        annotated.append({'id':i+1,'start':round(a,3),'end':round(b,3),'effect':proposed,
                          'zoom':1.0,'label':f'Escena {i+1}','effect_reason':reason})
    timeline={'version':2,'kind':'timeline','source':str(src),'duration':info['duration'],
              'platform':project.get('platform','youtube'),
              'profile':project.get('profile','freefire_short'),
              'effects':clip_effect,'composition':project.get('composition','fit'),
              'cut_style':'crossfade' if len(intervals)>1 and select_highlights else project.get('cut_style','hard'),
              'transition_seconds':0.25,
              'clips':annotated,
              'candidates':candidates[:40],
              'audio_silences':silences[:100],
              'scene_times':cuts,
              'subtitle_file':project.get('subtitle_file'),
              'watermark_file':project.get('watermark_file'),
              'narration_file':project.get('narration_file'),
              'notes':['Sugerencias técnicas, NO reconocimiento semántico de jugadas o memes',
                       'Los clips se editan manualmente antes de producir el MP4',
                       'Crossfade real requiere clips > transición y exportación FFmpeg'],
              'review_required':True}
    safe_write(filename,timeline)
    return timeline


def validate_timeline(tl):
    src=Path(tl['source'])
    info=probe(src)
    if not isinstance(tl.get('clips'),list) or not 1<=len(tl['clips'])<=100:
        raise ValueError('Timeline requiere entre 1 y 100 clips.')
    if tl.get('platform') not in ('youtube','shorts','tiktok'):
        raise ValueError('Plataforma inválida.')
    if tl.get('cut_style') not in ('hard','fade','crossfade'):
        raise ValueError('Transición inválida.')
    transition=float(tl.get('transition_seconds',.25))
    if not .05<=transition<=1.5:
        raise ValueError('Transición fuera de rango.')
    for clip in tl['clips']:
        a,b=float(clip['start']),float(clip['end'])
        if not (math.isfinite(a) and math.isfinite(b) and 0<=a<b<=info['duration']+.02):
            raise ValueError('Clip fuera de rango: '+str(clip))
        if clip.get('effect','clean') not in EFFECTS:
            raise ValueError('Efecto desconocido '+str(clip.get('effect')))
        if not 1<=float(clip.get('zoom',1))<=1.6:
            raise ValueError('Zoom fuera de rango (1–1.6)')
        if tl['cut_style']=='crossfade' and b-a < 2*transition:
            raise ValueError('Para crossfade cada clip debe durar al menos 2 veces la transición')
    return info


def apply_timeline(folder,*,overwrite=True):
    folder=Path(folder).resolve()
    tl=read_json(folder/'timeline-v2.json')
    if not tl:raise FileNotFoundError('No existe timeline-v2.json')
    validate_timeline(tl)
    plan_file=folder/'edit-plan.json'
    if plan_file.exists() and not overwrite:raise FileExistsError('El plan existente está protegido.')
    previous=read_json(plan_file,{})
    clips=[[float(x['start']),float(x['end'])] for x in tl['clips']]
    captions=read_srt(tl['subtitle_file']) if tl.get('subtitle_file') and Path(tl['subtitle_file']).is_file() else []
    subtitles=map_srt(captions,clips)
    if tl['cut_style']=='crossfade' and len(clips)>1:
        duration=float(tl['transition_seconds'])
        # Los tramos sucesivos empiezan antes por el solapamiento de la transición.
        for item in subtitles:
            offset=0.0
            for idx,(a,b) in enumerate(clips):
                offset+=b-a
                if item['start'] < offset:
                    item['start']=max(0,round(item['start']-idx*duration,3))
                    item['end']=max(item['start']+.08,round(item['end']-idx*duration,3))
                    break
    assets=read_json(folder/'project.json').get('meme_assets',[])
    plan={'schema':2,'project':str(folder),'source':tl['source'],
          'profile':tl['profile'],'platform':tl['platform'],
          'effects':tl['effects'],'composition':tl.get('composition','fit'),
          'cut_style':tl['cut_style'],'transition_seconds':tl['transition_seconds'],
          'clips':clips,'clip_effects':[x['effect'] for x in tl['clips']],
          'clip_zooms':[float(x.get('zoom',1)) for x in tl['clips']],
          'subtitles':subtitles,'watermark_file':tl.get('watermark_file'),
          'narration_file':tl.get('narration_file'),
          'meme_suggestions':suggest_memes(subtitles,assets),
          'meme_events_approved':previous.get('meme_events_approved',[]),
          'review_required':True,
          'analysis':{'mode':'phase2_suggested_timeline','candidate_count':len(tl.get('candidates',[])),
                      'warning':'Cortes sugeridos: análisis no semántico'}}
    safe_write(plan_file,plan)
    return plan


def still_preview(folder,clip_idx,out=None):
    tl=read_json(Path(folder)/'timeline-v2.json')
    validate_timeline(tl)
    clip=tl['clips'][clip_idx]
    path=Path(out) if out else Path(folder)/'previews'/f'shot-{clip_idx+1:03d}.jpg'
    path.parent.mkdir(parents=True,exist_ok=True)
    at=(clip['start']+clip['end'])/2
    run([required('ffmpeg'),'-hide_banner','-loglevel','error','-nostdin','-y',
         '-ss',str(at),'-i',tl['source'],'-frames:v','1','-vf',
         'scale=640:-2','-q:v','4',str(path)])
    return path


def transcribe_local(folder,model='small',device='cpu'):
    """Whisper local opcional; instalación/descarga del modelo se hace explícitamente."""
    if model not in ('tiny','base','small','medium') or device not in ('cpu','cuda'):
        raise ValueError('Modelo o acelerador no soportado')
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError('faster-whisper no instalado; instala: py -3 -m pip install faster-whisper') from exc
    folder=Path(folder).resolve()
    project=read_json(folder/'project.json')
    video=Path(project['source'])
    output=folder/'scripts'/'voz-original.srt'
    if output.exists():raise FileExistsError('La transcripción ya existe. No se sobrescribe.')
    engine=WhisperModel(model,device=device,compute_type='int8' if device=='cpu' else 'float16')
    sections,_=engine.transcribe(str(video),language='es',vad_filter=True)
    from .engine import write_srt
    items=[{'start':round(x.start,3),'end':round(x.end,3),'text':x.text.strip()}
           for x in sections if x.text.strip() and x.end>x.start]
    if not items:raise RuntimeError('No se detectaron palabras en la grabación')
    write_srt(items,output)
    project['subtitle_file']=str(output)
    safe_write(folder/'project.json',project)
    return {'subtitles':len(items),'file':str(output)}
