"""TokenLab native workspace panels. Model-dependent actions fail explicitly."""
import json
from pathlib import Path
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPlainTextEdit,
                               QPushButton,QComboBox,QSpinBox,QDoubleSpinBox,QTabWidget,QCheckBox)
from .tokenlab_tools import AtomicTaskCheckpoint
from .tokenlab_context import GestorContexto,deduplicate,prioritize
from .tokenlab_skills import RegistroSkills
from .tokenlab_ollama import summarize_ollama,embed_ollama
from .tokenlab_stream import OllamaStream
from .tokenlab_embed_async import OllamaEmbeddings
from .tokenlab_context_async import AsyncContextCompactor

def field(parent,title,height=80):
    parent.addWidget(QLabel(title))
    edit=QPlainTextEdit()
    edit.setFixedHeight(height)
    parent.addWidget(edit)
    return edit

class TokenLabAdvanced(QWidget):
    def __init__(self,model_combo,parent=None):
        super().__init__(parent)
        self.model_combo=model_combo
        self.storage=AtomicTaskCheckpoint()
        self.manager=None
        self.context_stream=OllamaStream(self)
        self.compactor=AsyncContextCompactor(None,self.context_stream,self)
        self.compactor.updated.connect(self._context_updated)
        self.compactor.progress.connect(self.mem_info_update)
        self.compactor.failed.connect(self.mem_error)
        self.compactor.cancelled.connect(lambda: self.mem_error("CANCELLED"))
        self.embed_stream=OllamaEmbeddings(self)
        self.embed_stream.completed.connect(self._embed_completed)
        self.embed_stream.failed.connect(self._embed_failed)
        self.embed_stream.cancelled.connect(self._embed_cancelled)
        self.pending_dedup=None
        self.live_stream=OllamaStream(self)
        self.live_stream.chunk.connect(self._live_chunk)
        self.live_stream.completed.connect(self._live_completed)
        self.live_stream.failed.connect(self._live_failed)
        self.live_stream.cancelled.connect(lambda: self._live_failed("CANCELLED"))
        self.live_mode=None
        self.live_skill=None
        self.registry=RegistroSkills(Path(__file__).parent.parent,summarizer=summarize_ollama)
        layout=QVBoxLayout(self)
        self.tabs=QTabWidget()
        layout.addWidget(self.tabs)
        self._memory()
        self._duplicate()
        self._priority()
        self._skills()

    def _memory(self):
        tab=QWidget(); v=QVBoxLayout(tab)
        self.permanent=field(v,"MEMORIA PERMANENTE · reglas protegidas",65)
        self.permanent.setPlainText("Respetar hechos verificables y conservar decisiones.")
        self.summary=field(v,"RESUMEN DE SESIÓN",55)
        self.summary.setReadOnly(True)
        self.volatile=field(v,"VENTANA VOLÁTIL · mensajes recientes",70)
        self.volatile.setReadOnly(True)
        self.message=field(v,"AGREGAR MENSAJE",55)
        row=QHBoxLayout()
        self.role=QComboBox();self.role.addItems(["user","assistant","tool"]);row.addWidget(self.role)
        self.budget=QSpinBox();self.budget.setRange(512,1_000_000);self.budget.setValue(8192);row.addWidget(self.budget)
        for title,method in (("NUEVA SESIÓN",self.new_context),("AGREGAR",self.add_message),
                             ("GUARDAR",self.save_context),("RECUPERAR",self.restore_context),
                             ("CANCELAR RESUMEN",self.compactor.cancel)):
            button=QPushButton(title);button.clicked.connect(method);row.addWidget(button)
        v.addLayout(row)
        self.mem_info=QLabel("Memoria todavía no iniciada.")
        self.mem_info.setWordWrap(True);v.addWidget(self.mem_info)
        self.tabs.addTab(tab,"Memoria 3 capas")

    def new_context(self):
        try:
            self.manager=GestorContexto(self.permanent.toPlainText(),self.budget.value(),
                                        modelo=self.model_combo.currentText(),
                                        reserva_respuesta=128,resumidor=summarize_ollama)
            self.compactor.manager=self.manager
            self.refresh_memory()
        except Exception as exc:
            self.mem_info.setText("ERROR: "+str(exc))
    def refresh_memory(self):
        if self.manager:
            state=self.manager.export()
            self.summary.setPlainText(state["resumen_sesion"])
            self.volatile.setPlainText(json.dumps(state["ventana_volatil"],ensure_ascii=False,indent=2))
            self.mem_info.setText("USO: {tokens}/{presupuesto} tokens. Resumen automático: Ollama local, modelo TOKENLAB_OLLAMA_MODEL.".format(**state))
    def add_message(self):
        try:
            if self.manager is None:self.new_context()
            if self.manager is not None:
                self.compactor.append(self.role.currentText(),self.message.toPlainText())
        except Exception as exc:
            self.mem_info.setText("ERROR: "+str(exc))
    def _context_updated(self, state):
        self.message.clear()
        self.refresh_memory()

    def mem_info_update(self,text):
        self.mem_info.setText(text)

    def mem_error(self,text):
        self.mem_info.setText("ERROR: "+str(text))

    def save_context(self):
        try:
            if self.manager is None:raise ValueError("Iniciar sesión primero")
            self.storage.save("studio_context",self.manager.export())
            self.mem_info.setText("Checkpoint de contexto guardado.")
        except Exception as exc:self.mem_info.setText("ERROR: "+str(exc))
    def restore_context(self):
        try:
            state=self.storage.load("studio_context")
            if not state:raise ValueError("Sin checkpoint de sesión")
            self.permanent.setPlainText(state["memoria_permanente"])
            self.new_context()
            self.manager.restore(state)
            self.refresh_memory()
        except Exception as exc:self.mem_info.setText("ERROR: "+str(exc))

    def _duplicate(self):
        tab=QWidget();v=QVBoxLayout(tab)
        self.dup_lines=field(v,"UN FRAGMENTO POR LÍNEA",115)
        row=QHBoxLayout()
        self.threshold=QDoubleSpinBox();self.threshold.setRange(0.5,1.0)
        self.threshold.setSingleStep(.01);self.threshold.setValue(.92)
        row.addWidget(QLabel("Umbral coseno"));row.addWidget(self.threshold)
        self.semantic=QCheckBox("Semántica real (Ollama /api/embed)")
        row.addWidget(self.semantic)
        button=QPushButton("ELIMINAR DUPLICADOS");button.clicked.connect(self.run_dedup)
        row.addWidget(button);v.addLayout(row)
        self.dup_result=field(v,"RESULTADOS ÚNICOS · exactos SHA-256",105)
        self.dup_result.setReadOnly(True)
        v.addWidget(QLabel("Para semántica: instala un modelo de embeddings real, por ejemplo: ollama pull nomic-embed-text."))
        self.tabs.addTab(tab,"Deduplicación")
    def run_dedup(self):
        try:
            items=[p for p in self.dup_lines.toPlainText().splitlines() if p.strip()]
            vectors=embed_ollama(items) if self.semantic.isChecked() else None
            self.dup_result.setPlainText("\n".join(deduplicate(items,embeddings=vectors,threshold=self.threshold.value())))
        except Exception as exc:self.dup_result.setPlainText("ERROR: "+str(exc))

    def _priority(self):
        tab=QWidget();v=QVBoxLayout(tab)
        self.priority_data=field(v,"CANDIDATOS JSON: [{text,embedding,recency,importance}]",85)
        self.query_vector=field(v,"VECTOR DE CONSULTA JSON: [0.1, 0.2, ...]",40)
        row=QHBoxLayout()
        self.priority_budget=QSpinBox();self.priority_budget.setRange(1,100000)
        self.priority_budget.setValue(1024);row.addWidget(self.priority_budget)
        button=QPushButton("SELECCIONAR SEGÚN 60/30/10");button.clicked.connect(self.run_priority)
        row.addWidget(button);v.addLayout(row)
        self.priority_result=field(v,"RESULTADO JSON ORDENADO POR PUNTUACIÓN",110)
        self.priority_result.setReadOnly(True)
        self.tabs.addTab(tab,"Priorización")
    def run_priority(self):
        try:
            items=json.loads(self.priority_data.toPlainText())
            q=json.loads(self.query_vector.toPlainText())
            report=prioritize(items,q,self.priority_budget.value(),self.model_combo.currentText())
            self.priority_result.setPlainText(json.dumps(report,ensure_ascii=False,indent=2))
        except Exception as exc:self.priority_result.setPlainText("ERROR: "+str(exc))

    def _skills(self):
        tab=QWidget();v=QVBoxLayout(tab)
        self.skill_select=QComboBox()
        self.skill_select.addItems(["buscar_repositorio","resumir","contar_tokens","comparar_prompts"])
        v.addWidget(self.skill_select)
        self.skill_args=field(v,'PARÁMETROS JSON (incluye max_results y max_tokens)',100)
        self.skill_args.setPlainText('{"texto":"Hola Dexter","max_results":5,"max_tokens":512}')
        action=QPushButton("EJECUTAR SKILL JSON");action.clicked.connect(self.run_skill)
        v.addWidget(action)
        self.skill_result=field(v,"RESPUESTA ESTRUCTURADA JSON",120)
        self.skill_result.setReadOnly(True)
        v.addWidget(QLabel("Resumen: Ollama local real (TOKENLAB_OLLAMA_MODEL). Si no está conectado, devuelve error JSON."))
        self._stream_ui(v)
        self.tabs.addTab(tab,"4 skills")
    def _stream_ui(self, parent):
        parent.addWidget(QLabel("INFERENCIA / RESUMEN EN STREAMING REAL · Ollama localhost"))
        self.live_prompt=field(parent,"PROMPT PARA EL MOTOR LOCAL",55)
        row=QHBoxLayout()
        for title,mode in (("INFERIR EN STREAMING","infer"),("RESUMIR EN STREAMING","summarize")):
            btn=QPushButton(title)
            btn.clicked.connect(lambda checked=False,m=mode:self.start_live(m))
            row.addWidget(btn)
        cancel=QPushButton("CANCELAR HTTP")
        cancel.clicked.connect(self.live_stream.cancel)
        row.addWidget(cancel)
        parent.addLayout(row)
        self.live_output=field(parent,"SALIDA PROGRESIVA DEL MODELO",80)
        self.live_output.setReadOnly(True)
        self.live_info=QLabel("Listo · Cancelar aborta la petición HTTP de Ollama.")
        self.live_info.setWordWrap(True)
        parent.addWidget(self.live_info)

    def start_live(self, mode, prompt=None, skill=None):
        try:
            if self.live_stream.active:
                raise RuntimeError("Hay una petición en curso")
            self.live_mode=mode
            self.live_skill=skill
            self.live_output.clear()
            self.live_info.setText("Conectando a Ollama…")
            self.live_stream.start(prompt if prompt is not None else self.live_prompt.toPlainText(),
                                   mode=mode,output_tokens=256)
        except Exception as exc:
            self._live_failed(type(exc).__name__ + ": " + str(exc))

    def _live_chunk(self, fragment):
        self.live_output.setPlainText(self.live_output.toPlainText()+fragment)
        self.live_info.setText("Recibiendo tokens reales…")

    def _live_completed(self, answer):
        self.live_info.setText("Completado: salida confirmada por Ollama.")
        if self.live_skill=="resumir":
            payload={"ok":True,"skill":"resumir","data":{"resumen":answer}}
            self.skill_result.setPlainText(json.dumps(payload,ensure_ascii=False))
        self.live_skill=None

    def _live_failed(self,reason):
        self.live_info.setText("ERROR: "+str(reason))
        if self.live_skill=="resumir":
            self.skill_result.setPlainText(json.dumps({"ok":False,"error":{"code":str(reason)}}))
        self.live_skill=None

    def run_skill(self):
        try:
            self.registry.model=self.model_combo.currentText()
            name=self.skill_select.currentText()
            args=json.loads(self.skill_args.toPlainText())
            if name=="resumir":
                if not isinstance(args,dict) or set(args)!={"texto","max_results","max_tokens"}:
                    raise ValueError("Parámetros estrictos inválidos")
                if not isinstance(args["texto"],str) or not args["texto"].strip():
                    raise ValueError("Texto inválido")
                if (type(args["max_tokens"]) is not int or not 64<=args["max_tokens"]<=8192 or
                    type(args["max_results"]) is not int or not 1<=args["max_results"]<=50):
                    raise ValueError("Límites inválidos")
                self.start_live("summarize",args["texto"],skill="resumir")
            else:
                self.skill_result.setPlainText(self.registry.execute_json(name,args))
        except Exception as exc:
            self.skill_result.setPlainText(json.dumps({"ok":False,"error":{"code":type(exc).__name__}}))
