"""Strict local function-call skills, with JSON outputs and bounded memoization."""
import hashlib
import json
from pathlib import Path
from .tokenlab_tools import compare_texts
from .tokenlab_context import tokens

class RegistroSkills:
    def __init__(self,repo_root,model="gpt-4o",summarizer=None):
        self.root=Path(repo_root).resolve()
        self.model=model
        self.summarizer=summarizer
        self.cache={}
        self.schemas={
            "buscar_repositorio":{"query":"string"},
            "resumir":{"texto":"string"},
            "contar_tokens":{"texto":"string"},
            "comparar_prompts":{"a":"string","b":"string"}
        }
    def specifications(self):
        out=[]
        for name,fields in self.schemas.items():
            properties={k:{"type":v,"description":k} for k,v in fields.items()}
            properties.update({"max_results":{"type":"integer","description":"result limit","minimum":1,"maximum":50},
                               "max_tokens":{"type":"integer","description":"output token limit","minimum":64,"maximum":8192}})
            out.append({"type":"function","function":{"name":name,"description":name,
                "strict":True,"parameters":{"type":"object","properties":properties,
                "required":list(properties),"additionalProperties":False}}})
        return out
    def execute(self,name,args):
        try:
            if name not in self.schemas:raise ValueError("Skill desconocida")
            fields=self.schemas[name]
            if not isinstance(args,dict) or set(args)!=set(fields)|{"max_results","max_tokens"}:
                raise ValueError("Parámetros no válidos")
            if any(not isinstance(args[k],str) or len(args[k])>100000 for k in fields):
                raise ValueError("Se requiere texto")
            if (type(args["max_results"]) is not int or not 1<=args["max_results"]<=50 or
                type(args["max_tokens"]) is not int or not 64<=args["max_tokens"]<=8192):
                raise ValueError("Límites inválidos")
            key=hashlib.sha256((name+"\0"+self.model+"\0"+json.dumps(args,ensure_ascii=False,sort_keys=True)).encode()).hexdigest()
            deterministic=name in ("contar_tokens","comparar_prompts")
            if deterministic and key in self.cache:
                data=self.cache[key]
            elif name=="contar_tokens":
                data={"tokens":tokens(args["texto"],self.model)}
            elif name=="comparar_prompts":
                data=compare_texts(args["a"],args["b"],self.model)
            elif name=="resumir":
                if self.summarizer is None:raise RuntimeError("Modelo real de resumen no configurado")
                data={"resumen":self.summarizer(args["texto"],args["max_tokens"]//2)}
            else:
                data=self._search(args["query"],args["max_results"])
            result={"ok":True,"skill":name,"data":data}
            if tokens(json.dumps(result,ensure_ascii=False),self.model)>args["max_tokens"]:
                raise ValueError("max_tokens excedido")
            if deterministic:
                if len(self.cache)>=128:self.cache.pop(next(iter(self.cache)))
                self.cache[key]=data
            return result
        except Exception as exc:
            return {"ok":False,"error":{"code":type(exc).__name__}}
    def execute_json(self,name,args):
        return json.dumps(self.execute(name,args),ensure_ascii=False,allow_nan=False)
    def _search(self,query,limit):
        result=[]
        if not query.strip():raise ValueError("Consulta vacía")
        skip={".git","node_modules","__pycache__",".venv","dist","build"}
        for path in sorted(self.root.rglob("*.py")):
            if len(result)>=limit:break
            if path.is_symlink() or not path.is_file() or path.stat().st_size>350000:
                continue
            if any(x in skip for x in path.relative_to(self.root).parts):continue
            try:
                for line_no,line in enumerate(path.read_text(encoding="utf-8").splitlines(),1):
                    if query.casefold() in line.casefold():
                        result.append({"path":str(path.relative_to(self.root)),"line":line_no,
                                       "match":line[:180]})
                        if len(result)>=limit:break
            except (OSError,UnicodeError):continue
        return {"matches":result}
