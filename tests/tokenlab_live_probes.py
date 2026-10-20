"""Opt-in real inference probes. No fake provider, no response content or keys logged."""
from __future__ import annotations
import json
import os
import time
import urllib.request
import urllib.error

def post_json(url: str, body: dict, headers: dict | None = None, timeout=180) -> tuple[dict,float]:
    raw=json.dumps(body).encode("utf-8")
    req=urllib.request.Request(url,raw,headers={"Content-Type":"application/json",**(headers or {})},method="POST")
    start=time.monotonic()
    with urllib.request.urlopen(req,timeout=timeout) as response:
        result=json.load(response)
    return result,round((time.monotonic()-start)*1000,2)

def live_ollama(model: str | None = None):
    model=model or os.getenv("OLLAMA_TEST_MODEL","llama3.2:1b")
    base=os.getenv("OLLAMA_URL","http://127.0.0.1:11434").rstrip("/")
    timings=[]
    results=[]
    for prompt in ("Responde con una sola palabra: Hola.", "Responde con una sola palabra: Adiós."):
        answer,ms=post_json(base+"/api/generate",{
            "model":model,"prompt":prompt,"stream":False,
            "options":{"num_predict":24,"temperature":0,"num_ctx":512}
        },timeout=240)
        if answer.get("done") is not True or not isinstance(answer.get("response"),str) or not answer["response"].strip():
            raise AssertionError("Ollama no devolvió una respuesta completada")
        if not isinstance(answer.get("eval_count"),int):
            raise AssertionError("Ollama no devolvió conteo de tokens de salida")
        timings.append(ms)
        results.append({"prompt_eval_count":answer.get("prompt_eval_count"),"eval_count":answer["eval_count"]})
    return {"provider":"ollama","real_inference":True,"model":model,
            "latency_ms":timings,"ab_token_usage":results,
            "comparison":"Dos prompts diferentes inferidos; respuestas no almacenadas."}

def live_openai():
    key=os.getenv("OPENAI_API_KEY","")
    if not key:
        return {"provider":"openai","status":"SKIPPED_NO_OPENAI_API_KEY","real_inference":False}
    model=os.getenv("OPENAI_TEST_MODEL","gpt-4.1-mini")
    answer,ms=post_json("https://api.openai.com/v1/responses",
        {"model":model,"input":"Responde solamente OK.","max_output_tokens":24},
        headers={"Authorization":"Bearer "+key},timeout=90)
    if answer.get("status")!="completed" or not answer.get("output"):
        raise AssertionError("OpenAI no devolvió response completado")
    usage=answer.get("usage",{})
    return {"provider":"openai","real_inference":True,"model":model,
            "latency_ms":ms,"input_tokens":usage.get("input_tokens"),
            "output_tokens":usage.get("output_tokens"),"status":"completed"}

if __name__=="__main__":
    provider=os.environ.get("TOKENLAB_PROBE","ollama")
    try:
        result=live_ollama() if provider=="ollama" else live_openai() if provider=="openai" else None
        if result is None:
            raise ValueError("TOKENLAB_PROBE inválido")
        print(json.dumps(result,ensure_ascii=False))
    except (OSError,ValueError,AssertionError,urllib.error.HTTPError) as exc:
        # Never print request headers or credentials.
        print(json.dumps({"provider":provider,"status":"FAILED",
                          "error_type":type(exc).__name__}))
        raise SystemExit(1)
