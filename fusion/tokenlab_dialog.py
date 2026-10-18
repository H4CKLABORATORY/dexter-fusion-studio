"""TokenLab's real native PySide6 panel, opened from the main editor toolbar."""
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,
                               QPlainTextEdit,QPushButton,QComboBox,QMessageBox)
from .tokenlab_tools import compare_texts,AtomicTaskCheckpoint,TokenLabUnavailable
from .tokenlab_advanced import TokenLabAdvanced

class TokenLabDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle("TOKENLAB · DEXTER FUSION STUDIO")
        self.resize(980,890)
        self.storage=AtomicTaskCheckpoint()
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel("PROMPT A · BASE ORIGINAL"))
        self.a=QPlainTextEdit(self); self.a.setFixedHeight(68); layout.addWidget(self.a)
        layout.addWidget(QLabel("PROMPT B · VERSIÓN OPTIMIZADA"))
        self.b=QPlainTextEdit(self); self.b.setFixedHeight(68); layout.addWidget(self.b)
        row=QHBoxLayout()
        self.model=QComboBox(self)
        self.model.addItems(["gpt-4o","gpt-4o-mini","gpt-4.1","gpt-4.1-mini","gpt-5"])
        row.addWidget(self.model)
        compare=QPushButton("COMPARAR TOKENS A/B",self)
        compare.clicked.connect(self.compare);row.addWidget(compare)
        store=QPushButton("GUARDAR CHECKPOINT",self)
        store.clicked.connect(self.save);row.addWidget(store)
        layout.addLayout(row)
        self.result=QLabel("Conteo pendiente: requiere tiktoken instalado.",self)
        self.result.setWordWrap(True);layout.addWidget(self.result)
        self.workspace=TokenLabAdvanced(self.model,self)
        layout.addWidget(self.workspace,1)
        try:
            saved=self.storage.load("studio_ab")
            if saved:
                self.a.setPlainText(saved.get("a",""))
                self.b.setPlainText(saved.get("b",""))
        except (OSError,ValueError,TypeError):
            self.result.setText("No se pudo recuperar el checkpoint; no se modificaron los prompts.")

    def compare(self):
        try:
            report=compare_texts(self.a.toPlainText(),self.b.toPlainText(),self.model.currentText())
            self.result.setText("A: {a_tokens} · B: {b_tokens} · Diferencia: {difference} · Ahorro: {savings_pct}% · Encoding: {encoding}".format(**report))
        except (TokenLabUnavailable,ValueError,TypeError) as exc:
            self.result.setText("Conteo no disponible: "+str(exc))

    def save(self):
        try:
            self.storage.save("studio_ab",{"a":self.a.toPlainText(),"b":self.b.toPlainText()})
            self.result.setText("Checkpoint guardado en Documentos/DexterFusionStudio/tokenlab.")
        except (OSError,TypeError,ValueError) as exc:
            QMessageBox.warning(self,"TokenLab",str(exc))
