"""Real loopback HTTP tests for asynchronous Qt transport: no fake Ollama results."""
import json
import os
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
    from fusion.tokenlab_stream import OllamaStream, local_url
except ImportError:
    QApplication = None


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length))
        if self.path != "/api/generate" or request.get("stream") is not True:
            self.send_error(400)
            return
        prompt = request.get("prompt", "")
        if "FAIL_503" in prompt:
            self.send_response(503)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.end_headers()
        if "SLOW_REQUEST" in prompt:
            time.sleep(0.5)
        frames = (b'{"response":"Hola ","done":false}\n',
                  b'{"response":"mundo","done":false}\n',
                  b'{"response":"","done":true}\n')
        if "BROKEN_FRAME" in prompt:
            frames = (b"not-a-json-frame\n",)
        for frame in frames:
            try:
                self.wfile.write(frame)
                self.wfile.flush()
                time.sleep(.01)
            except (BrokenPipeError, ConnectionResetError):
                break
    def log_message(self, *_):
        pass


@unittest.skipIf(APPLICATION_MISSING := QApplication is None, "PySide6 unavailable; Qt CI covers these tests")
class TokenLabStreamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.server.daemon_threads = True
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = "http://127.0.0.1:" + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def collect(self, prompt, timeout_ms=2000, cancel=False):
        worker = OllamaStream(timeout_ms=timeout_ms, server=self.url)
        result = {"chunks": [], "done": [], "error": [], "cancelled": []}
        worker.chunk.connect(result["chunks"].append)
        worker.completed.connect(result["done"].append)
        worker.failed.connect(result["error"].append)
        worker.cancelled.connect(lambda: result["cancelled"].append(True))
        worker.start(prompt)
        if cancel:
            worker.cancel()
        limit = time.monotonic() + 3.0
        while worker.active and time.monotonic() < limit:
            self.app.processEvents()
            time.sleep(.005)
        self.app.processEvents()
        self.assertFalse(worker.active, "Qt streaming did not complete")
        return result

    def test_stream_success_and_progressive_chunks(self):
        result = self.collect("HELLO")
        self.assertEqual(result["done"], ["Hola mundo"])
        self.assertEqual("".join(result["chunks"]), "Hola mundo")
        self.assertFalse(result["error"] or result["cancelled"])

    def test_real_http_abort(self):
        result = self.collect("SLOW_REQUEST", cancel=True)
        self.assertEqual(result["cancelled"], [True])
        self.assertFalse(result["done"])
        self.assertFalse(result["error"])

    def test_timeout(self):
        result = self.collect("SLOW_REQUEST", timeout_ms=60)
        self.assertEqual(result["error"], ["TIMEOUT"])
        self.assertFalse(result["done"])

    def test_provider_http_error(self):
        result = self.collect("FAIL_503")
        self.assertEqual(result["error"], ["HTTP_503"])
        self.assertFalse(result["done"])

    def test_bad_ndjson(self):
        result = self.collect("BROKEN_FRAME")
        self.assertEqual(result["error"], ["INVALID_NDJSON"])
        self.assertFalse(result["done"])

    def test_reject_external_host_and_credentials(self):
        for url in ("https://example.com:11434", "http://evil.com:11434",
                    "http://me:pass@127.0.0.1:11434", "http://127.0.0.1:11434/api"):
            with self.assertRaises(ValueError):
                local_url(url)
