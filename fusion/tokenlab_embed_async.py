"""Async native Qt adapter for REAL Ollama /api/embed vectors.

No model is simulated; UI is responsive during network I/O.
Cancel/timeout must never publish an embedding vector.
"""
from __future__ import annotations

import json
import math
import os

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from .tokenlab_stream import local_url


class OllamaEmbeddings(QObject):
    completed = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, parent=None, timeout_ms=60000, server=None):
        super().__init__(parent)
        if type(timeout_ms) is not int or not 50 <= timeout_ms <= 600000:
            raise ValueError("Timeout inválido")
        self.server = local_url(server or os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"))
        self.manager = QNetworkAccessManager(self)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._timeout)
        self.timeout_ms = timeout_ms
        self.reply = None
        self.active = False
        self.reason = ""
        self.expected = 0

    def start(self, texts, model=None):
        if self.active:
            raise RuntimeError("Ya hay una operación de embeddings en curso")
        if (not isinstance(texts, list) or not 1 <= len(texts) <= 128
                or any(not isinstance(s, str) or not s.strip()
                       or len(s) > 10000 for s in texts)):
            raise ValueError("Textos de embeddings inválidos")
        model = model or os.getenv("TOKENLAB_EMBED_MODEL", "nomic-embed-text")
        if not isinstance(model, str) or not 1 <= len(model) <= 128:
            raise ValueError("Nombre de modelo inválido")
        body = json.dumps({"model": model, "input": texts}, ensure_ascii=False).encode("utf-8")
        request = QNetworkRequest(QUrl(self.server + "/api/embed"))
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        self.reason = ""
        self.expected = len(texts)
        self.active = True
        self.reply = self.manager.post(request, body)
        self.reply.finished.connect(self._finish)
        self.timer.start(self.timeout_ms)

    def cancel(self):
        if self.active and self.reply:
            self.reason = "cancelled"
            self.timer.stop()
            self.reply.abort()

    def _timeout(self):
        if self.active and self.reply:
            self.reason = "timeout"
            self.reply.abort()

    def _finish(self):
        if not self.active:
            return
        self.timer.stop()
        response = self.reply
        reason = self.reason
        self.active = False
        self.reply = None
        if reason == "cancelled":
            response.deleteLater()
            self.cancelled.emit()
            return
        if reason:
            response.deleteLater()
            self.failed.emit(reason.upper())
            return
        status = response.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        if status is not None and int(status) >= 400:
            response.deleteLater()
            self.failed.emit("HTTP_" + str(status))
            return
        if response.error() != QNetworkReply.NetworkError.NoError:
            error_code = response.error().name
            response.deleteLater()
            self.failed.emit("NETWORK_" + error_code)
            return
        if response.bytesAvailable() > 8_000_000:
            response.deleteLater()
            self.failed.emit("OVERSIZE_RESPONSE")
            return
        raw = bytes(response.readAll())
        response.deleteLater()
        try:
            payload = json.loads(raw)
            vectors = payload["embeddings"]
            if not isinstance(vectors, list) or len(vectors) != self.expected:
                raise ValueError("Dimensión/cantidad inválidas")
            lengths = set()
            for vector in vectors:
                if not isinstance(vector, list) or not vector or len(vector) > 16384:
                    raise ValueError("Vector inválido")
                for value in vector:
                    if type(value) not in (int, float) or not math.isfinite(value):
                        raise ValueError("Valor de embedding no finito")
                if not any(value != 0 for value in vector):
                    raise ValueError("Vector nulo")
                lengths.add(len(vector))
            if len(lengths) != 1:
                raise ValueError("Dimensiones distintas")
        except (KeyError, TypeError, ValueError, UnicodeDecodeError):
            self.failed.emit("INVALID_EMBEDDINGS")
            return
        self.completed.emit(vectors)
