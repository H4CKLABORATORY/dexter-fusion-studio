"""TokenLab context: loss-aware three-layer memory and bounded prioritization.

The summarizer is injected: no fake summaries are produced when a model is absent.
Embedding similarities are accepted only when explicitly supplied by a real provider.
"""
from __future__ import annotations
from dataclasses import dataclass,field
from math import sqrt,isfinite
import json,re
from .tokenlab_tools import counter_for_model,exact_sha256

def tokens(text: str,model="gpt-4o") -> int:
    if not isinstance(text,str): raise TypeError("texto inválido")
    return len(counter_for_model(model).encode(text))

def cosine(a,b):
    if not a or not b or len(a)!=len(b) or any(not isfinite(float(x)) for x in list(a)+list(b)):
        raise ValueError("Embeddings incompatibles")
    na=sqrt(sum(float(v)**2 for v in a)); nb=sqrt(sum(float(v)**2 for v in b))
    if not na or not nb: raise ValueError("Embedding nulo")
    return sum(float(x)*float(y) for x,y in zip(a,b))/(na*nb)

def deduplicate(fragments,embeddings=None,threshold=0.92):
    """Keep distinct facts, even if near-identical vector positions."""
    if not 0<=threshold<=1: raise ValueError("Umbral inválido")
    if embeddings is not None and len(fragments)!=len(embeddings):
        raise ValueError("Embeddings incompletos")
    seen=set(); kept=[]; indices=[]
    for i,part in enumerate(fragments):
        if not isinstance(part,str): raise TypeError("Texto inválido")
        digest=exact_sha256(part.strip())
        if digest in seen: continue
        similar=False
        if embeddings is not None:
            for j in indices:
                # Protect changes in numeric facts and explicit negation markers.
                facts=lambda s: (re.findall(r"\b\d+(?:[.,]\d+)?\b",s),
                                 re.findall(r"\b(?:no|nunca|sin|not|never|without)\b",s,re.I))
                if facts(part)!=facts(fragments[j]): continue
                if cosine(embeddings[i],embeddings[j])>=threshold:
                    similar=True; break
        if not similar:
            kept.append(part); indices.append(i); seen.add(digest)
    return kept

def prioritize(candidates,query_embedding,token_limit,model="gpt-4o"):
    """Score 60% semantic + 30% recency + 10% declared importance."""
    if not isinstance(token_limit,int) or token_limit<0: raise ValueError("Presupuesto inválido")
    scored=[]
    for i,item in enumerate(candidates):
        if not isinstance(item.get("text"),str): raise TypeError("Candidato sin texto")
        emb=item.get("embedding")
        semantic=max(0,min(1,cosine(query_embedding,emb))) if emb is not None else 0
        recency=float(item.get("recency",0)); importance=float(item.get("importance",0))
        if any(not isfinite(x) or x<0 or x>1 for x in (recency,importance)):
            raise ValueError("Recencia/importancia deben estar en [0,1]")
        scored.append((round(.6*semantic+.3*recency+.1*importance,7),-i,item))
    total=0; selected=[]
    for score,_,item in sorted(scored,reverse=True):
        cost=tokens(item["text"],model)
        if cost+total<=token_limit:
            selected.append({"text":item["text"],"score":score,"tokens":cost});total+=cost
    return {"selected":selected,"total_tokens":total,"budget":token_limit}

@dataclass
class GestorContexto:
    memoria_permanente: str
    limite_tokens: int
    modelo: str="gpt-4o"
    reserva_respuesta: int=256
    resumen_max_tokens: int=512
    resumidor: object=None
    hechos_obligatorios: list=field(default_factory=list)
    resumen_sesion: str=""
    ventana_volatil: list=field(default_factory=list)

    def __post_init__(self):
        if self.limite_tokens<=self.reserva_respuesta or self.resumen_max_tokens<1:
            raise ValueError("Configuración de tokens inválida")
        if self.token_count()>self.budget:
            raise ValueError("Memoria permanente supera el límite y nunca se recorta")

    @property
    def budget(self): return self.limite_tokens-self.reserva_respuesta

    def _serialized(self,summary,messages):
        return json.dumps({"permanente":self.memoria_permanente,"resumen":summary,
                           "mensajes":messages},ensure_ascii=False,separators=(",",":"))

    def token_count(self):
        return tokens(self._serialized(self.resumen_sesion,self.ventana_volatil),self.modelo)

    def add(self,role,text):
        if role not in ("user","assistant","tool") or not isinstance(text,str):
            raise ValueError("Mensaje inválido")
        copy=[dict(m) for m in self.ventana_volatil]+[{"role":role,"content":text}]
        summary=self.resumen_sesion
        while tokens(self._serialized(summary,copy),self.modelo)>self.budget:
            if len(copy)<2: raise ValueError("Último mensaje excede presupuesto disponible")
            if self.resumidor is None:
                raise RuntimeError("Resumen automático necesita un modelo real configurado")
            oldest=copy.pop(0)
            old_text=("Resumen previo:\n"+summary+"\n" if summary else "")+oldest["role"]+": "+oldest["content"]
            updated=self.resumidor(old_text,self.resumen_max_tokens)
            if not isinstance(updated,str) or not updated.strip():
                raise ValueError("Resumidor no devolvió texto")
            if any(not isinstance(f,str) or (f and f not in updated) for f in self.hechos_obligatorios):
                raise ValueError("El resumen perdió un hecho protegido")
            if tokens(updated,self.modelo)>self.resumen_max_tokens:
                raise ValueError("Resumen supera límite")
            summary=updated
        # Publish only after compaction has succeeded completely.
        self.ventana_volatil=copy;self.resumen_sesion=summary
        return self.export()

    def export(self):
        return {"memoria_permanente":self.memoria_permanente,
                "resumen_sesion":self.resumen_sesion,
                "ventana_volatil":[dict(m) for m in self.ventana_volatil],
                "tokens":self.token_count(),"presupuesto":self.budget}

    def restore(self,saved):
        if saved.get("memoria_permanente")!=self.memoria_permanente:
            raise ValueError("Reglas permanentes cambiaron, restauración rechazada")
        summary=saved.get("resumen_sesion");messages=saved.get("ventana_volatil")
        if not isinstance(summary,str) or not isinstance(messages,list) or any(
            not isinstance(m,dict) or m.get("role") not in ("user","assistant","tool")
            or not isinstance(m.get("content"),str) for m in messages):
            raise ValueError("Checkpoint inválido")
        if tokens(self._serialized(summary,messages),self.modelo)>self.budget:
            raise ValueError("Checkpoint excede presupuesto")
        self.resumen_sesion=summary;self.ventana_volatil=[dict(m) for m in messages]
