"""TokenLab native workspace panels. Model-dependent actions fail explicitly."""
import json
from pathlib import Path
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPlainTextEdit,
                               QPushButton,QComboBox,QSpinBox,QDoubleSpinBox,QTabWidget)
from .tokenlab_tools import AtomicTaskCheckpoint
from .tokenlab_context import GestorContexto,deduplicate,prioritize
from .tokenlab_skills import RegistroSkills

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
        self.registry=RegistroSkills(Path(__file__).parent.parent)
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
                             ("GUARDAR",self.save_context),("RECUPERAR",self.restore_context)):
            button=QPushButton(title);button.clicked.connect(method);row.addWidget(button)
        v.addLayout(row)
        self.mem_info=QLabel("Memoria todavía no iniciada.")
        self.mem_info.setWordWrap(True);v.addWidget(self.mem_info)
        self.tabs.addTab(tab,"Memoria 3 capas")

    def new_context(self):
        try:
            self.manager=GestorContexto(self.permanent.toPlainText(),self.budget.value(),
                                        modelo=self.model_combo.currentText(),
                                        reserva_respuesta=128)
            self.refresh_memory()
        except Exception as exc:
            self.mem_info.setText("ERROR: "+str(exc))
    def refresh_memory(self):
        if self.manager:
            state=self.manager.export()
            self.summary.setPlainText(state["resumen_sesion"])
            self.volatile.setPlainText(json.dumps(state["ventana_volatil"],ensure_ascii=False,indent=2))
            self.mem_info.setText("USO: {tokens}/{presupuesto} tokens. Compresión requiere resumidor real configurado.".format(**state))
    def add_message(self):
        try:
            if self.manager is None:self.new_context()
            if self.manager is not None:
                self.manager.add(self.role.currentText(),self.message.toPlainText())
                self.message.clear()
                self.refresh_memory()
        except Exception as exc:
            self.mem_info.setText("ERROR: "+str(exc))
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
        button=QPushButton("ELIMINAR DUPLICADOS");button.clicked.connect(self.run_dedup)
        row.addWidget(button);v.addLayout(row)
        self.dup_result=field(v,"RESULTADOS ÚNICOS · exactos SHA-256",105)
        self.dup_result.setReadOnly(True)
        v.addWidget(QLabel("Deduplicación semántica requiere embeddings reales configurados. No se simula con palabras."))
        self.tabs.addTab(tab,"Deduplicación")
    def run_dedup(self):
        try:
            items=[p for p in self.dup_lines.toPlainText().splitlines() if p.strip()]
            self.dup_result.setPlainText("\n".join(deduplicate(items,threshold=self.threshold.value())))
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
        v.addWidget(QLabel("La skill de resumen requiere un modelo real. Sin él devuelve un error JSON."))
        self.tabs.addTab(tab,"4 skills")
    def run_skill(self):
        try:
            self.registry.model=self.model_combo.currentText()
            self.skill_result.setPlainText(self.registry.execute_json(
                self.skill_select.currentText(),json.loads(self.skill_args.toPlainText())))
        except Exception as exc:
            self.skill_result.setPlainText(json.dumps({"ok":False,"error":{"code":type(exc).__name__}}))
