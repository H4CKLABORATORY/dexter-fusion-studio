"""Escaneo FFmpeg/FFprobe. Nunca inventa detección de contexto."""
from __future__ import annotations
import json, re, shutil, subprocess
from pathlib import Path

def required(binary):
    exe=shutil.which(binary)
    if not exe: raise RuntimeError(f'Falta {binary} instalado en el equipo. No se ha procesado ningún video.')
    return exe

def run(cmd,*,cwd=None):
    result=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace',cwd=cwd)
    if result.returncode: raise RuntimeError((result.stderr or result.stdout)[-2500:])
    return result

def probe(source):
    binary=required('ffprobe')
    data=json.loads(run([binary,'-v','error','-show_entries','stream=index,codec_type,codec_name,width,height,avg_frame_rate:format=duration', '-of','json',str(source)]).stdout)
    video=next((s for s in data.get('streams',[]) if s['codec_type']=='video'),None)
    if video is None: raise ValueError('No hay pista de video')
    return {'duration':float(data.get('format',{}).get('duration') or 0),
            'width':int(video.get('width') or 0),'height':int(video.get('height') or 0),
            'fps':video.get('avg_frame_rate',''),
            'audio':any(s['codec_type']=='audio' for s in data.get('streams',[]))}

def silence_ranges(source, minimum=.5, threshold='-34dB'):
    binary=required('ffmpeg')
    result=subprocess.run([binary,'-hide_banner','-nostdin','-i',str(source),'-af',f'silencedetect=noise={threshold}:d={minimum}','-vn','-f','null','-'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace')
    if result.returncode:raise RuntimeError(result.stderr[-1900:])
    periods=[]; start=None
    for line in result.stderr.splitlines():
        a=re.search(r'silence_start:\s*(\d+(?:\.\d+)?)',line)
        b=re.search(r'silence_end:\s*(\d+(?:\.\d+)?)',line)
        if a:start=float(a.group(1))
        if b and start is not None:
            end=float(b.group(1))
            if end>start:periods.append([round(start,3),round(end,3)])
            start=None
    if start is not None:
        periods.append([start,probe(source)['duration']])
    return periods

def keep_ranges(duration,silences, pad=.12,min_keep=.75):
    position=0.; result=[]
    for a,b in sorted(silences):
        stop=max(position,a-pad)
        if stop-position>=min_keep:result.append([round(position,3),round(stop,3)])
        position=max(position,b+pad)
    if duration-position>=min_keep:result.append([round(position,3),round(duration,3)])
    return result or ([[0.,round(duration,3)]] if duration>0 else [])

def select_segments(ranges,target=0):
    if not target:return ranges
    out=[]; pos=0.
    for s,e in ranges:
        remaining=target-pos
        if remaining<=0:break
        stop=min(e,s+remaining)
        if stop>s:out.append([s,round(stop,3)]); pos+=stop-s
    return out

def scene_changes(source, threshold=.37, max_seconds=180):
    """Cortes visuales aproximados por histograma. Opción acotada para no exigir mucha CPU."""
    binary=required('ffmpeg')
    cmd=[binary,'-hide_banner','-nostdin','-i',str(source),'-t',str(max_seconds),'-vf',f"select='gt(scene,{threshold})',showinfo",'-an','-f','null','-']
    result=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace')
    # El filtro showinfo comunica sus marcas en stderr.
    return sorted({round(float(x),3) for x in re.findall(r'pts_time:(\d+(?:\.\d+)?)',result.stderr)})
