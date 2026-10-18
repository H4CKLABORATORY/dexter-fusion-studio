"""Real local Ollama adapter, never substitutes fake output for missing models.

Requests are sent to configured local Ollama only, without third-party proxy.
"""
import json
import os
import urllib.request
from urllib.parse import urlsplit

def _url():
    """Reject non-loopback hosts, URL credentials, paths and redirects."""
    endpoint=os.getenv("OLLAMA_URL","http://127.0.0.1:11434").rstrip("/")
    parsed=urlsplit(endpoint)
    try:
        valid=(parsed.scheme=="http"
               and parsed.hostname in ("127.0.0.1","localhost","::1")
               and parsed.port is not None
               and parsed.username is None and parsed.password is None
               and parsed.path in ("","/") and not parsed.query and not parsed.fragment)
    except ValueError:
        valid=False
    if not valid:
        raise ValueError("Ollama debe ser una URL HTTP loopback sin credenciales")
    return endpoint

def _post(path,payload,timeout=90):
    req=urllib.request.Request(_url()+path,data=json.dumps(payload).encode(),
                               headers={"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=timeout) as response:
        return json.load(response)

def summarize_ollama(text,max_tokens=256):
    if not isinstance(text,str) or not 1<=max_tokens<=2048:
        raise ValueError("Parámetros de resumen inválidos")
    model=os.getenv("TOKENLAB_OLLAMA_MODEL","llama3.2:1b")
    request=("Resume exclusivamente el contenido a continuación en español. "
             "Conserva todos los hechos, cifras, nombres, decisiones y detalles técnicos exactos. "
             "No inventes contenido, ni obvies contradicciones. Responde SOLO con el resumen.\n\n"
             +text)
    result=_post("/api/generate",{"model":model,"prompt":request,"stream":False,
                                  "options":{"num_predict":max_tokens,"temperature":0}},timeout=180)
    answer=result.get("response")
    if result.get("done") is not True or not isinstance(answer,str) or not answer.strip():
        raise RuntimeError("Ollama no generó un resumen válido")
    return answer.strip()

def embed_ollama(texts):
    if not isinstance(texts,list) or not texts or any(not isinstance(x,str) for x in texts):
        raise ValueError("Textos de embeddings inválidos")
    model=os.getenv("TOKENLAB_EMBED_MODEL","nomic-embed-text")
    result=_post("/api/embed",{"model":model,"input":texts},timeout=120)
    embeddings=result.get("embeddings")
    if not isinstance(embeddings,list) or len(embeddings)!=len(texts) or not all(
        isinstance(v,list) and v for v in embeddings):
        raise RuntimeError("Ollama no devolvió embeddings válidos")
    return embeddings
