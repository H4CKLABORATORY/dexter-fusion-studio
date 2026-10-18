"""Transaction-safe asynchronous memory compaction for the Qt event loop.

Only after all required Ollama summaries have completed is the new state
published; aborting, timing out, or a provider error preserves prior messages.
"""
from __future__ import annotations

import json
from PySide6.QtCore import QObject, Signal
from .tokenlab_context import tokens


class AsyncContextCompactor(QObject):
    updated = Signal(object)
    progress = Signal(str)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, manager, stream, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.stream = stream
        self.pending = None
        stream.completed.connect(self._summary_completed)
        stream.failed.connect(self._failed)
        stream.cancelled.connect(self._cancelled)

    @property
    def busy(self):
        return self.pending is not None

    def append(self, role, text):
        if self.busy:
            raise RuntimeError("Una compresión ya está en curso")
        if self.manager is None:
            raise RuntimeError("Primero crea una sesión")
        if role not in ("user", "assistant", "tool") or not isinstance(text, str):
            raise ValueError("Mensaje inválido")
        # Prepare a shadow copy; do not mutate the live manager on failure.
        shadow = self.manager.export()
        shadow["ventana_volatil"].append({"role": role, "content": text})
        self.pending = shadow
        try:
            self._advance()
        except Exception:
            self.pending = None
            raise

    def cancel(self):
        if self.busy and self.stream.active:
            self.stream.cancel()

    def _advance(self):
        state = self.pending
        if state is None:
            return
        m = self.manager
        while tokens(m._serialized(state["resumen_sesion"], state["ventana_volatil"]), m.modelo) > m.budget:
            if len(state["ventana_volatil"]) < 2:
                raise ValueError("El último mensaje excede el presupuesto")
            oldest = state["ventana_volatil"].pop(0)
            old = state["resumen_sesion"]
            fragment = ("Resumen anterior:\n" + old + "\n" if old else "")
            fragment += oldest["role"] + ": " + oldest["content"]
            self.progress.emit("Resumiendo contexto en Ollama…")
            self.stream.start(fragment, mode="summarize",
                              output_tokens=m.resumen_max_tokens)
            return

        # Atomic in-memory update, after every summary has passed validation.
        saved_messages = state["ventana_volatil"]
        saved_summary = state["resumen_sesion"]
        m.ventana_volatil = [dict(item) for item in saved_messages]
        m.resumen_sesion = saved_summary
        self.pending = None
        self.updated.emit(m.export())

    def _summary_completed(self, summary):
        if not self.busy:
            return
        m = self.manager
        try:
            if not isinstance(summary, str) or not summary.strip():
                raise ValueError("Resumen vacío")
            if tokens(summary, m.modelo) > m.resumen_max_tokens:
                raise ValueError("Resumen excede presupuesto")
            if any(not isinstance(fact, str) or (fact and fact not in summary)
                   for fact in m.hechos_obligatorios):
                raise ValueError("El resumen perdió un hecho protegido")
            self.pending["resumen_sesion"] = summary
            self._advance()
        except Exception as exc:
            self.pending = None
            self.failed.emit(type(exc).__name__ + ": " + str(exc))

    def _failed(self, reason):
        if self.busy:
            self.pending = None
            self.failed.emit(reason)

    def _cancelled(self):
        if self.busy:
            self.pending = None
            self.cancelled.emit()
