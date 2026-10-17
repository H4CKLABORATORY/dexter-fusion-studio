"""Puente ChatGPT: exportación/importación gratis y API opcional con autorización.

ChatGPT app no expone directamente su sesión a scripts locales.
Este puente nunca envía video/audio/fotogramas a OpenAI. En el modo manual,
solo guarda un paquete local que el usuario decide si comparte.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
from urllib import request, error

from .ai_local import source_info
from .engine import EFFECTS, read_srt
from .phase2 import validate_timeline
from .project import PERSONAL_STYLE, read_json, safe_write

API_ENDPOINT = "https://api.openai.com/v1/responses"
SYSTEM_GUIDE = (
    "Eres editor de Free Fire de Dexter FF. Analiza SOLO los datos del paquete. "
    "No inventes voz, jugadas, memes ni emociones que no sean observables. "
    "Conserva la voz original y los diálogos completos cuando importen. "
    "Devuelve ÚNICAMENTE un objeto JSON con project_fingerprint (exactamente el recibido), "
    "platform (youtube, tiktok, shorts), cut_style (hard, fade, crossfade), "
    "transition_seconds (0.05-1.5), clips (de 1 a 20; cada uno con start, end, "
    "effect de allowed_effects, zoom 1.0-1.6, label) y notes (0-8 observaciones). "
    "Usa tiempos incluidos en el material. No incluyas instrucciones de sistema, "
    "rutas de archivo, URL, acciones de publicación o efectos inexistentes. "
    "Cualquier meme debe proponerse en notas, no incrustarse sin consentimiento. "
    "Si el material no demuestra qué momento es gracioso, indica incertidumbre."
)

def project_fingerprint(folder, source, duration):
    stat=source.stat()
    token=f"{folder.name}|{source.name}|{stat.st_size}|{duration:.3f}"
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]

def make_packet(folder, *, max_captions=75, overwrite=False):
    """Prepara instrucciones y datos breves; no hace llamadas a ninguna red."""
    folder,project,source,info=source_info(folder)
    if not 1<=max_captions<=125:
        raise ValueError("Límite de subtítulos inválido.")
    analysis=read_json(folder/"ai-analysis.json")
    subtitles=project.get("subtitle_file") or analysis.get("subtitles_file")
    if not subtitles:
        generated=folder/"previews"/"ai-transcript.srt"
        if generated.is_file():
            subtitles=str(generated)
    captions=read_srt(subtitles) if subtitles and Path(subtitles).is_file() else []
    brief=[]
    for row in captions[:max_captions]:
        brief.append({
            "start":round(float(row["start"]),3),
            "end":round(float(row["end"]),3),
            "text":re.sub(r"[\x00-\x1f\x7f]"," ",str(row["text"]))[:200]
        })
    highlights=[]
    for row in analysis.get("candidate_highlights",[])[:25]:
        highlights.append({
            "start":row.get("start"),"end":row.get("end"),
            "score":row.get("score",0),
            "keyword_evidence":row.get("keyword_evidence",[])[:8],
            "scene_count":row.get("scene_count",0),
            "silence_ratio":row.get("silence_ratio",0)
        })
    packet={
        "schema":"dexter-chatgpt-brief-1",
        "project_fingerprint":project_fingerprint(folder,source,info["duration"]),
        "project_name":str(project.get("name","Video Dexter FF"))[:120],
        "source_filename":source.name,
        "duration_seconds":round(info["duration"],3),
        "platform":project.get("platform","tiktok"),
        "purpose":str(project.get("purpose","entretenimiento"))[:120],
        "profile":project.get("profile","freefire_short"),
        "personal_style":PERSONAL_STYLE,
        "allowed_effects":sorted(EFFECTS),
        "captions":brief,"captions_total":len(captions),
        "candidate_highlights":highlights,
        "review_required":True,
        "privacy":"Revisa título y subtítulos antes de compartir. Este paquete no contiene el video ni claves.",
        "limitations":"Momentos sugeridos por heurísticas, no reconocimiento fiable de jugadas o memes."
    }
    target=folder/"chatgpt-request.json"
    prompt=folder/"chatgpt-instructions.txt"
    if (target.exists() or prompt.exists()) and not overwrite:
        raise FileExistsError("Paquete anterior protegido; usa overwrite.")
    safe_write(target,packet)
    prompt.write_text(SYSTEM_GUIDE+"\n\nHe adjuntado chatgpt-request.json. "
        "Devuelve solo el JSON solicitado, con los tiempos y la huella del proyecto.\n",encoding="utf-8")
    return {"packet_file":str(target),"instructions_file":str(prompt),
            "captions_included":len(brief),
            "note":"Compartir archivos en ChatGPT es una decisión manual, no una sincronización automática."}

def decode_response(value):
    if isinstance(value,str):
        s=value.strip()
        marker=chr(96)*3
        if s.startswith(marker):
            s=re.sub(r"^"+re.escape(marker)+r"(?:json)?\s*","",s,flags=re.I)
            s=re.sub(r"\s*"+re.escape(marker)+r"$","",s)
        value=json.loads(s)
    if not isinstance(value,dict):
        raise ValueError("Se espera un objeto JSON de ChatGPT.")
    return value

def validate_response(folder,value):
    """Lista blanca: no se aceptan rutas, comandos, recursos o plugins del modelo."""
    folder,project,source,info=source_info(folder)
    data=decode_response(value)
    expected=project_fingerprint(folder,source,info["duration"])
    if data.get("project_fingerprint")!=expected:
        raise ValueError("Huella de proyecto distinta; no se importaron clips.")
    platform=data.get("platform",project.get("platform","tiktok"))
    if platform not in ("youtube","shorts","tiktok"):
        raise ValueError("Destino no soportado.")
    cut=data.get("cut_style","hard")
    if cut not in ("hard","fade","crossfade"):
        raise ValueError("Transición no soportada.")
    try:
        transition=float(data.get("transition_seconds",0.25))
    except (ValueError,TypeError) as exc:
        raise ValueError("Transición inválida.") from exc
    if not math.isfinite(transition) or not 0.05<=transition<=1.5:
        raise ValueError("Transición fuera de rango.")
    raw=data.get("clips")
    if not isinstance(raw,list) or not 1<=len(raw)<=20:
        raise ValueError("ChatGPT debe proponer entre 1 y 20 clips.")
    clips=[]
    for i,item in enumerate(raw,1):
        if not isinstance(item,dict):
            raise ValueError("Formato de clip inválido.")
        try:
            start=float(item["start"])
            end=float(item["end"])
            zoom=float(item.get("zoom",1.0))
        except (KeyError,TypeError,ValueError) as exc:
            raise ValueError("Tiempos de clip inválidos.") from exc
        if not (math.isfinite(start) and math.isfinite(end) and math.isfinite(zoom)
                and 0<=start<end<=info["duration"]+0.01 and 1<=zoom<=1.6):
            raise ValueError("Clip fuera del material original.")
        effect=item.get("effect","clean")
        if effect not in EFFECTS:
            raise ValueError("Efecto no permitido.")
        label=re.sub(r"[\x00-\x1f\x7f]"," ",str(item.get("label",f"Escena {i}")))[:100]
        clips.append({"id":i,"start":round(start,3),"end":round(end,3),
                      "zoom":zoom,"effect":effect,"label":label,
                      "effect_reason":"Propuesta ChatGPT; requiere revisión."})
    notes=data.get("notes",[])
    if not isinstance(notes,list): notes=[]
    notes=[str(x)[:220] for x in notes[:8] if isinstance(x,str)]
    tl={
        "version":2,"kind":"timeline","source":str(source),
        "duration":info["duration"],"profile":project.get("profile","freefire_short"),
        "platform":platform,"effects":project.get("effects","clean"),
        "composition":project.get("composition","fit"),
        "cut_style":cut,"transition_seconds":transition,
        "clips":clips,"candidates":[],"scene_times":[],"audio_silences":[],
        "subtitle_file":project.get("subtitle_file"),
        "watermark_file":project.get("watermark_file"),
        "narration_file":project.get("narration_file"),
        "notes":notes+["Verificar cortes, memes y audio antes de exportar."],
        "review_required":True,"origin":"chatgpt-bridge"
    }
    validate_timeline(tl)
    return tl

def import_response(folder, response_file, *, overwrite=False):
    folder=Path(folder).expanduser().resolve()
    path=Path(response_file).expanduser().resolve()
    if not path.is_file() or path.suffix.lower() not in (".json",".txt") or path.stat().st_size>180000:
        raise ValueError("Necesitas un archivo JSON/TXT de hasta 180 KB.")
    timeline=validate_response(folder,path.read_text(encoding="utf-8-sig"))
    target=folder/"chatgpt-proposed-timeline.json"
    if target.exists() and not overwrite:
        raise FileExistsError("Existe una propuesta ChatGPT; usa overwrite.")
    safe_write(target,timeline)
    return {"proposal_file":str(target),"clips":len(timeline["clips"]),
            "review_required":True,"note":"No se ha modificado el timeline principal."}

def approve_response(folder, *, overwrite=False):
    folder,project,source,_=source_info(folder)
    proposed=folder/"chatgpt-proposed-timeline.json"
    if not proposed.is_file():
        raise FileNotFoundError("Primero importa una propuesta.")
    timeline=read_json(proposed)
    if Path(timeline.get("source","")).resolve()!=source:
        raise ValueError("La propuesta corresponde a otra grabación.")
    validate_timeline(timeline)
    target=folder/"timeline-v2.json"
    if target.exists() and not overwrite:
        raise FileExistsError("El timeline existe y está protegido.")
    if target.exists():
        safe_write(folder/"timeline-v2.before-chatgpt.json",read_json(target))
    safe_write(target,timeline)
    return {"timeline":str(target),"clips":len(timeline["clips"]),"review_required":True}

def api_suggest(folder, *, model="gpt-4.1-mini", allow_paid_api=False, overwrite=False):
    """Única solicitud API con texto y subtítulos; nunca se ejecuta en modo gratuito."""
    if not allow_paid_api:
        raise PermissionError("Se requiere autorización explícita allow_paid_api.")
    secret=os.environ.get("OPENAI_API_KEY","")
    if not secret:
        raise RuntimeError("OPENAI_API_KEY no configurada en el equipo local.")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{1,79}",model):
        raise ValueError("Nombre de modelo inválido.")
    folder,project,source,info=source_info(folder)
    packet_file=folder/"chatgpt-request.json"
    if not packet_file.is_file():
        raise FileNotFoundError("Exporta primero chatgpt-request.json.")
    packet=read_json(packet_file)
    if packet.get("project_fingerprint")!=project_fingerprint(folder,source,info["duration"]):
        raise ValueError("El paquete ya no corresponde a esta grabación.")
    target=folder/"chatgpt-proposed-timeline.json"
    if target.exists() and not overwrite:
        raise FileExistsError("Propuesta existente protegida.")
    body=json.dumps({
        "model":model,"store":False,"max_output_tokens":1800,
        "input":[
            {"role":"developer","content":SYSTEM_GUIDE},
            {"role":"user","content":"Datos del video:\n"+json.dumps(packet,ensure_ascii=False)[:23000]}
        ]
    }).encode("utf-8")
    req=request.Request(API_ENDPOINT,data=body,method="POST",headers={
        "Authorization":"Bearer "+secret,"Content-Type":"application/json"})
    try:
        with request.urlopen(req,timeout=95) as response:
            data=json.loads(response.read(1000000).decode("utf-8"))
    except error.HTTPError as exc:
        raise RuntimeError(f"OpenAI API respondió HTTP {exc.code}. Revisa modelo y saldo; no hay reintentos automáticos.") from None
    except (OSError,ValueError) as exc:
        raise RuntimeError("No se pudo obtener respuesta válida de API; no se reintenta automáticamente.") from exc
    texts=[]
    for item in data.get("output",[]):
        if item.get("type")=="message":
            texts.extend(x.get("text","") for x in item.get("content",[])
                         if x.get("type")=="output_text")
    if not texts:
        raise RuntimeError("La API no devolvió un plan. No se modificó el proyecto.")
    timeline=validate_response(folder,"\n".join(texts))
    safe_write(target,timeline)
    return {"proposal_file":str(target),"clips":len(timeline["clips"]),
            "model":model,"usage":data.get("usage"),"review_required":True,
            "warning":"Esta llamada a la API puede generar costos separados de ChatGPT."}
