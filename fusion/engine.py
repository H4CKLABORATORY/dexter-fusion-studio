"""Edición automatizada conservadora: FFmpeg, cortes, efectos, subtítulos, memes.

No promete reconocer el contenido emocional, decidir memes contextuales ni replicar
los 170/306 efectos de editores externos. Las operaciones son transparentes.
"""
from __future__ import annotations
import json, subprocess, tempfile, shutil
from pathlib import Path
from .media import required,run,probe,silence_ranges,keep_ranges,select_segments,scene_changes
from .project import read_json,safe_write
from .caption_styles import CAPTION_STYLES,write_ass

OUTPUTS={'youtube':(1920,1080),'shorts':(1080,1920),'tiktok':(1080,1920)}
EFFECTS={
    'clean': {'label':'Natural, legible','filter':'eq=contrast=1.03:saturation=1.06'},
    'hype': {'label':'Free Fire: energía','filter':'eq=contrast=1.10:saturation=1.20,unsharp=5:5:0.65'},
    'cinematic':{'label':'Cinemático','filter':'eq=contrast=1.09:saturation=0.98:gamma=1.02,vignette=PI/6'},
    'retro':{'label':'Retro meme','filter':'eq=contrast=1.09:saturation=0.75,hue=h=8'},
    'monochrome':{'label':'Dramático B/N','filter':'hue=s=0,eq=contrast=1.13'},
    'none':{'label':'Original','filter':'null'},
    'neon':{'label':'Neón Free Fire','filter':'eq=contrast=1.18:saturation=1.42,unsharp=5:5:0.7'},
    'comic':{'label':'Comic / memes','filter':'eq=contrast=1.23:saturation=1.34,unsharp=7:7:0.85'},
    'cold':{'label':'Frío azul','filter':'colorbalance=rs=-.05:gs=0:bs=.10,eq=contrast=1.06'},
    'warm':{'label':'Cálido','filter':'colorbalance=rs=.07:gs=.025:bs=-.06,eq=saturation=1.08'},
    'dream':{'label':'Sueño suave','filter':'gblur=sigma=1.1,eq=gamma=1.04:saturation=0.90'},
    'glitch':{'label':'Glitch RGB ligero','filter':'rgbashift=rh=4:bh=-4,eq=contrast=1.12:saturation=1.15'},
    'vhs':{'label':'VHS / retro','filter':'noise=alls=11:allf=t+u,eq=saturation=.80'},
    'night':{'label':'Noche dramática','filter':'eq=brightness=-.03:contrast=1.18:saturation=.83'},
    'flash':{'label':'Destello','filter':'eq=brightness=.095:contrast=1.04:saturation=1.16'},
    'soft':{'label':'Belleza suave','filter':'gblur=sigma=0.55,eq=brightness=.025:saturation=1.08'},
    'sharp':{'label':'Alta nitidez','filter':'unsharp=7:7:1.0,eq=contrast=1.07:saturation=1.08'}
}

def srt_seconds(value):
    v=value.strip().replace('.',',')
    h,m,s=v.split(':'); sec,mill=s.split(',')
    return int(h)*3600+int(m)*60+int(sec)+int(mill)/1000

def srt_stamp(seconds):
    v=round(max(0,seconds)*1000)
    h,v=divmod(v,3600000);m,v=divmod(v,60000);s,ms=divmod(v,1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'

def read_srt(path):
    import re
    items=[]
    for block in re.split(r'\n\s*\n',Path(path).read_text(encoding='utf-8-sig').replace('\r','').strip()):
        lines=block.splitlines()
        idx=next((i for i,x in enumerate(lines) if '-->' in x),None)
        if idx is None:continue
        a,b=(x.strip() for x in lines[idx].split('-->',1))
        text=' '.join(lines[idx+1:]).strip()
        if text:items.append({'start':srt_seconds(a),'end':srt_seconds(b),'text':text})
    return items

def map_srt(items,clips):
    out=[];offset=0
    for s,e in clips:
        for line in items:
            a=max(s,line['start']);b=min(e,line['end'])
            if b-a>=.08:
                out.append({'start':round(offset+a-s,3),'end':round(offset+b-s,3),'text':line['text']})
        offset+=e-s
    return out

def write_srt(items,path):
    Path(path).write_text(''.join(f'{i}\n{srt_stamp(x["start"])} --> {srt_stamp(x["end"])}\n{x["text"]}\n\n' for i,x in enumerate(items,1)),encoding='utf-8')

def suggest_memes(subtitles,assets,max_events=7):
    """Coincidencia exacta de etiquetas, no comprensión automática de chistes."""
    import re
    out=[]
    for sub in subtitles:
        if len(out)>=max_events:break
        lower=sub['text'].casefold()
        for a in assets:
            if not a.get('approved',False):continue
            if not Path(a['path']).is_file():continue
            tags=[str(t).casefold() for t in a.get('tags',[])]
            match=next((tag for tag in tags if re.search(r'(?<!\w)'+re.escape(tag)+r'(?!\w)',lower)),None)
            if match and (not out or sub['start']-out[-1]['start']>=2.5):
                out.append({'path':a['path'],'start':sub['start'],'end':sub['start']+1.3,
                            'trigger':match,'approved':False,'reason':'Etiquetas; confirmar relevancia antes de renderizar'})
                break
    return out

def generate_plan(folder, *, auto_silence=False, max_duration=None, scene_scan=False):
    folder=Path(folder)
    project=read_json(folder/'project.json')
    src=Path(project.get('source',''))
    if not src.is_file():raise FileNotFoundError(f'Video original no encontrado: {src}')
    info=probe(src)
    if not info['duration']:raise ValueError('No se detectó duración del video')
    silence=silence_ranges(src) if auto_silence and info['audio'] else []
    clips=keep_ranges(info['duration'],silence,min_keep=float(project.get('minimum_clip',1.1))) if silence else [[0,info['duration']]]
    maximum=float(max_duration if max_duration is not None else project.get('maximum_length',0))
    if maximum>0:clips=select_segments(clips,maximum)
    if not clips:raise ValueError('No quedaron segmentos después del análisis')
    subtitles=[]
    if project.get('subtitle_file') and Path(project['subtitle_file']).is_file():
        subtitles=map_srt(read_srt(project['subtitle_file']),clips)
    assets=project.get('meme_assets',[])
    analysis={'media':info, 'silences':silence,
              'scene_changes':scene_changes(src) if scene_scan else [],
              'limits':'Detección técnica: no evalúa qué meme es gracioso ni identifica automáticamente jugadas de Free Fire.'}
    plan={'schema':1,'project':str(folder),'profile':project.get('profile','generic'),
          'platform':project.get('platform','youtube'),'effects':project.get('effects','clean'),
          'composition':project.get('composition','fit'),'cut_style':project.get('cut_style','hard'),
          'caption_style':project.get('caption_style','classic'),
          'source':str(src),'clips':clips,'subtitles':subtitles,
          'meme_suggestions':suggest_memes(subtitles,assets),
          'meme_events_approved':[], 'watermark_file':project.get('watermark_file'),
          'narration_file':project.get('narration_file'),
          'review_required':True,'analysis':analysis}
    safe_write(folder/'edit-plan.json',plan)
    return plan

def validate_plan(plan):
    source=Path(plan['source']).expanduser().resolve()
    info=probe(source)
    clips=plan['clips']
    if not clips or len(clips)>100:raise ValueError('Cantidad de cortes no válida')
    prev=-1
    for a,b in clips:
        if not(0<=a<b<=info['duration']+.05 and a>=prev): raise ValueError('Cortes fuera de tiempo o desordenados')
        prev=b
    if plan['platform'] not in OUTPUTS:raise ValueError('Formato de publicación desconocido')
    if plan['effects'] not in EFFECTS:raise ValueError('Efecto no soportado')
    if plan.get('caption_style','classic') not in CAPTION_STYLES:raise ValueError('Estilo de subtítulo desconocido')
    if plan.get('composition','fit') not in ('fit','crop'):raise ValueError('Encuadre no soportado')
    if plan.get('cut_style','hard') not in ('hard','fade','crossfade'):raise ValueError('Transición no soportada')
    overrides=plan.get('clip_effects',[])
    zooms=plan.get('clip_zooms',[])
    if overrides and (len(overrides)!=len(clips) or any(e not in EFFECTS for e in overrides)):
        raise ValueError('Efectos individuales de clips inválidos')
    if zooms and (len(zooms)!=len(clips) or any(not 1<=float(z)<=1.6 for z in zooms)):
        raise ValueError('Zoom individual inválido')
    if plan.get('cut_style')=='crossfade' and len(clips)>1:
        t=float(plan.get('transition_seconds',.25))
        if not .05<=t<=1.5 or any(b-a<2*t for a,b in clips):
            raise ValueError('Crossfade no válido: revisa duración de clips y transición')
    return info

def fit_filter(width,height,mode):
    if mode=='crop':
        return f'scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,crop={width}:{height},setsar=1'
    return f'scale={width}:{height}:force_original_aspect_ratio=decrease:flags=lanczos,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,setsar=1'

def crossfade_parts(parts,durations,transition,output):
    """Real crossfade video + audio between normalized local MP4 segments.

    Inputs are already scaled to identical dimensions, fps, channel layout.
    This reencodes stitched material but never overwrites originals.
    """
    if len(parts)<2:raise ValueError('Crossfade requiere 2 clips.')
    exe=required('ffmpeg')
    args=[exe,'-hide_banner','-loglevel','error','-nostdin','-y']
    for clip in parts:args+=['-i',str(clip)]
    filters=[]
    # Input clips are CFR 30 and share video/audio specifications.
    video='[0:v]';audio='[0:a]';running=durations[0]
    for i in range(1,len(parts)):
        offset=max(0.0,running-transition)
        filters.append(f'{video}[{i}:v]xfade=transition=fade:duration={transition:.3f}:offset={offset:.3f}[vx{i}]')
        filters.append(f'{audio}[{i}:a]acrossfade=d={transition:.3f}:c1=tri:c2=tri[ax{i}]')
        video=f'[vx{i}]';audio=f'[ax{i}]';running+=durations[i]-transition
    args+=['-filter_complex',';'.join(filters),'-map',video,'-map',audio,
           '-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p',
           '-c:a','aac','-b:a','160k',str(output)]
    run(args)
    return output

def export_plan(folder,*,overwrite=False,verify=True):
    folder=Path(folder).expanduser().resolve()
    plan=read_json(folder/'edit-plan.json')
    info=validate_plan(plan)
    exe=required('ffmpeg')
    width,height=OUTPUTS[plan['platform']]
    target=folder/'output'/f'{plan["platform"]}-{plan["effects"]}.mp4'
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists() and not overwrite:raise FileExistsError('Ya existe una exportación. Activa sobrescribir para continuar.')
    all_duration=sum(e-s for s,e in plan['clips'])
    with tempfile.TemporaryDirectory(prefix='fusion-',dir=folder) as tmp:
        work=Path(tmp); parts=[]
        for i,(a,b) in enumerate(plan['clips']):
            duration=b-a;dest=work/f'clip-{i:03}.mp4'
            effect=plan.get('clip_effects',[])
            effect=effect[i] if effect else plan['effects']
            vf=fit_filter(width,height,plan.get('composition','fit'))+','+EFFECTS[effect]['filter']
            zooms=plan.get('clip_zooms',[])
            zoom=float(zooms[i]) if zooms else 1.0
            if zoom>1.001:
                zw=int(width/zoom)//2*2; zh=int(height/zoom)//2*2
                vf+=f',crop={zw}:{zh}:(iw-ow)/2:(ih-oh)/2,scale={width}:{height}:flags=lanczos'
            if plan.get('cut_style')=='fade':
                d=min(.20,duration/4)
                vf+=f',fade=t=in:st=0:d={d:.3f},fade=t=out:st={duration-d:.3f}:d={d:.3f}'
            vf+=',format=yuv420p'
            cmd=[exe,'-hide_banner','-loglevel','error','-nostdin','-y','-ss',str(a),'-i',plan['source']]
            if not info['audio']:cmd+=['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']
            cmd+=['-t',str(duration),'-map','0:v:0','-map','0:a:0' if info['audio'] else '1:a:0',
                  '-vf',vf,'-r','30','-c:v','libx264','-crf','21','-preset','veryfast',
                  '-c:a','aac','-ar','48000','-ac','2','-b:a','160k','-shortest',str(dest)]
            run(cmd);parts.append(dest)
        if plan.get('cut_style')=='crossfade' and len(parts)>1:
            joined=work/'joined.mp4'
            crossfade_parts(parts,[b-a for a,b in plan['clips']],float(plan.get('transition_seconds',.25)),joined)
        else:
            joined=None
        manifest=work/'concat.txt'
        manifest.write_text(''.join("file '"+str(p).replace("'","'\\''")+"'\n" for p in parts),encoding='utf-8')
        if joined is None:
            joined=work/'joined.mp4'
            run([exe,'-hide_banner','-loglevel','error','-nostdin','-y','-safe','0','-f','concat','-i',str(manifest),'-c','copy',str(joined)])
        # Reencode final for captions, watermark, optional narration and approved images.
        cmd=[exe,'-hide_banner','-loglevel','error','-nostdin','-y','-i',str(joined)]
        overlays=[]
        if plan.get('watermark_file'):
            watermark=Path(plan['watermark_file']).expanduser().resolve()
            if not watermark.is_file() or watermark.suffix.lower() not in ('.png','.webp'):raise ValueError('Marca de agua incompatible')
            overlays.append((watermark,None))
        for ev in plan.get('meme_events_approved',[]):
            pic=Path(ev['path']).expanduser().resolve()
            if not pic.is_file() or pic.suffix.lower() not in ('.png','.jpg','.jpeg','.webp'):raise ValueError('Meme de imagen incompatible')
            if not 0<=float(ev['start'])<float(ev['end'])<=all_duration+.1:raise ValueError('Tiempo de meme fuera de rango')
            overlays.append((pic,ev))
        if len(overlays)>14:raise ValueError('Máximo 14 imágenes superpuestas')
        for pic,_ in overlays:cmd+=['-loop','1','-i',str(pic)]
        narration=plan.get('narration_file')
        if narration:
            voice=Path(narration).expanduser().resolve()
            if not voice.is_file() or voice.suffix.lower() not in ('.wav','.mp3','.m4a'):raise ValueError('Narración no encontrada')
            cmd+=['-i',str(voice)]
        filters=[]; current='[0:v]'; count=0
        if plan.get('subtitles'):
            style=plan.get('caption_style','classic')
            if style=='classic':
                write_srt(plan['subtitles'],work/'captions.srt')
                subtitle_file='captions.srt'
            else:
                write_ass(plan['subtitles'],work/'captions.ass',width=width,height=height,style=style)
                subtitle_file='captions.ass'
            filters.append(f'{current}subtitles={subtitle_file}[v0]')
            current='[v0]'
        for idx,(_,event) in enumerate(overlays,1):
            ih=int(height*(.12 if event is None else .23))
            filters.append(f'[{idx}:v]scale=-1:{ih},format=rgba[img{idx}]')
            condition="" if event is None else f":enable='between(t,{float(event['start']):.3f},{float(event['end']):.3f})'"
            x,y=('W-w-30','30') if event is None else ('W-w-30',f'H-h-{int(height*.16)}')
            nextname=f'[ov{idx}]'
            filters.append(f'{current}[img{idx}]overlay=x={x}:y={y}{condition}{nextname}')
            current=nextname
        if narration:
            voiceidx=len(overlays)+1
            filters.append(f'[0:a]volume=0.40[game];[{voiceidx}:a]volume=1.0[voice];[game][voice]amix=inputs=2:duration=first:dropout_transition=0[mixed]')
        if filters:
            cmd+=['-filter_complex',';'.join(filters),'-map',current]
        else:cmd+=['-map','0:v:0']
        cmd+=['-map','[mixed]' if narration else '0:a:0',
              '-c:v','libx264','-crf','20','-preset','medium','-pix_fmt','yuv420p',
              '-c:a','aac','-b:a','192k','-movflags','+faststart',str(target)]
        run(cmd,cwd=work)
    if verify:
        final=probe(target)
        if target.stat().st_size<=1024 or final['duration']<=0:raise RuntimeError('Exportación inválida')
    return target
