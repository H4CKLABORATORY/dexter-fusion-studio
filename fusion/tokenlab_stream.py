"""Non-blocking real Ollama streaming on Qt event loop.

QNetworkReply.abort() is real transport cancellation. Never commit partial
summaries on cancellation, HTTP errors, timeout, or malformed provider frames.
"""
from __future__ import annotations

import json
import os
from urllib.parse import urlsplit

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtCore import QUrl


def local_url(value: str) -> str:
    """Refuse remote URLs and unexpected schemes for local-model requests."""
    parsed = urlsplit(value)
    if parsed.scheme != "http" or parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("El servidor Ollama debe estar en localhost")
    if parsed.username or parsed.password or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise ValueError("URL Ollama inválida")
    if parsed.port is None or not 1 <= parsed.port <= 65535:
        raise ValueError("Indica el puerto HTTP de Ollama")
    return value.rstrip("/")


class OllamaStream(QObject):
    """Consumes Ollama /api/generate NDJSON without blocking Qt.

    Event signals: chunk(text), completed(text), failed(code), cancelled().
    The caller owns the QObject on Qt's main thread. No fake inference.
    """

    chunk = Signal(str)
    completed = Signal(str)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, parent=None, timeout_ms=90000, server=None):
        super().__init__(parent)
        if not isinstance(timeout_ms, int) or not 50 <= timeout_ms <= 600000:
            raise ValueError("Timeout inválido")
        self.server = local_url(server or os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"))
        self.manager = QNetworkAccessManager(self)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._timeout)
        self.timeout_ms = timeout_ms
        self.reply = None
        self.buffer = bytearray()
        self.parts = []
        self.done = False
        self.stop_reason = ""
        self.active = False

    def start(self, prompt: str, mode="infer", model=None, output_tokens=256):
        if self.active:
            raise RuntimeError("Ya existe una solicitud en curso")
        if mode not in ("infer", "summarize") or not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Modo o prompt inválido")
        if not isinstance(output_tokens, int) or not 1 <= output_tokens <= 2048:
            raise ValueError("Límite de salida inválido")
        model = model or os.getenv("TOKENLAB_OLLAMA_MODEL", "llama3.2:1b")
        if not isinstance(model, str) or not 1 <= len(model) <= 128:
            raise ValueError("Modelo inválido")
        if mode == "summarize":
            prompt = ("Resume SOLO los hechos aportados. Conserva cifras, nombres, "
                      "decisiones y detalles técnicos exactos, sin inventar información. "
                      "No ocultes contradicciones.\n\n" + prompt)
        body = json.dumps({"model": model, "prompt": prompt, "stream": True,
                           "options": {"num_predict": output_tokens, "temperature": 0}}).encode("utf-8")
        request = QNetworkRequest(QUrl(self.server + "/api/generate"))
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        self.buffer.clear()
        self.parts = []
        self.done = False
        self.stop_reason = ""
        self.active = True
        self.reply = self.manager.post(request, body)
        self.reply.readyRead.connect(self._consume)
        self.reply.finished.connect(self._finish)
        self.timer.start(self.timeout_ms)

    def cancel(self):
        if self.active and self.reply is not None:
            self.stop_reason = "cancelled"
            self.timer.stop()
            self.reply.abort()

    def _timeout(self):
        if self.active and self.reply is not None:
            self.stop_reason = "timeout"
            self.reply.abort()

    def _consume(self):
        if not self.active or self.reply is None or self.stop_reason:
            return
        self.buffer.extend(bytes(self.reply.readAll()))
        if len(self.buffer) > 1_000_000:
            self.stop_reason = "oversize"
            self.reply.abort()
            return
        while b"\n" in self.buffer:
            frame, _, rest = self.buffer.partition(b"\n")
            self.buffer = bytearray(rest)
            if not frame.strip():
                continue
            try:
                obj = json.loads(frame)
                if not isinstance(obj, dict):
                    raise ValueError("frame not object")
                if obj.get("error"):
                    self.stop_reason = "provider_error"
                    self.reply.abort()
                    return
                fragment = obj.get("response", "")
                if not isinstance(fragment, str):
                    raise ValueError("invalid response field")
                if fragment:
                    self.parts.append(fragment)
                    self.chunk.emit(fragment)
                if obj.get("done") is True:
                    self.done = True
            except (ValueError, UnicodeError):
                self.stop_reason = "invalid_ndjson"
                self.reply.abort()
                return

    def _finish(self):
        if not self.active:
            return
        self.timer.stop()
        response = self.reply
        if not self.stop_reason:
            self._consume()
        status = response.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        self.active = False
        self.reply = None
        response.deleteLater()
        if self.stop_reason == "cancelled":
            self.cancelled.emit()
        elif self.stop_reason:
            self.failed.emit(self.stop_reason.upper())
        elif status is not None and int(status) >= 400:
            self.failed.emit("HTTP_" + str(status))
        elif not self.done or not "".join(self.parts).strip():
            self.failed.emit("INCOMPLETE_RESPONSE")
        else:
            self.completed.emit("".join(self.parts))
