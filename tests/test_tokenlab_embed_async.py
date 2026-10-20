"""Qt semantic embedding adapter contract using loopback HTTP, not an LLM."""
import json
import os
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
try:
    from PySide6.QtWidgets import QApplication
    from fusion.tokenlab_embed_async import OllamaEmbeddings
except ImportError:
    QApplication=None

class EmbeddedHttp(BaseHTTPRequestHandler):
    def do_POST(self):
        raw=self.rfile.read(int(self.headers.get("Content-Length","0")))
        body=json.loads(raw)
        if self.path!="/api/embed":
            self.send_error(404)
            return
        if body.get("input")==["HTTP_503"]:
            self.send_error(503)
            return
        if body.get("input")==["WAIT_FOR_CANCEL"]:
            time.sleep(.35)
        texts=body["input"]
        if texts==["INVALID_VECTORS"]:
            payload={"embeddings":[[float("nan")]]}
        elif texts==["INVALID_COUNT"]:
            payload={"embeddings":[]}
        elif texts==["BAD_JSON"]:
            payload={"embeddings":"not-a-vector"}
        else:
            payload={"embeddings":[([1.0,0.0] if t=="Igual" else [0.0,1.0]) for t in texts]}
        data=json.dumps(payload).encode()
        try:
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError,ConnectionResetError):
            return
    def log_message(self,*args):
        pass

@unittest.skipIf(QApplication is None,"Qt ausente; el runner Qt y Windows ejecuta estas pruebas")
class EmbedQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        cls.http=ThreadingHTTPServer(("127.0.0.1",0),EmbeddedHttp)
        cls.http.daemon_threads=True
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True)
        cls.thread.start()
        cls.url=f"http://127.0.0.1:{cls.http.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join(timeout=3)

    def run_embed(self,texts,timeout_ms=1500,cancel=False):
        worker=OllamaEmbeddings(server=self.url,timeout_ms=timeout_ms)
        result={"done":[],"error":[],"cancel":[]}
        worker.completed.connect(result["done"].append)
        worker.failed.connect(result["error"].append)
        worker.cancelled.connect(lambda:result["cancel"].append(True))
        worker.start(texts)
        if cancel:worker.cancel()
        deadline=time.monotonic()+3
        while worker.active and time.monotonic()<deadline:
            self.app.processEvents()
            time.sleep(.004)
        self.app.processEvents()
        self.assertFalse(worker.active)
        return result

    def test_success(self):
        result=self.run_embed(["Igual","Igual","Distinto"])
        self.assertEqual(result["done"],[[[1.0,0.0],[1.0,0.0],[0.0,1.0]]])
        self.assertFalse(result["error"] or result["cancel"])

    def test_cancel_aborts_transport(self):
        result=self.run_embed(["WAIT_FOR_CANCEL"],cancel=True)
        self.assertEqual(result["cancel"],[True])
        self.assertFalse(result["done"])

    def test_timeout_does_not_publish(self):
        result=self.run_embed(["WAIT_FOR_CANCEL"],timeout_ms=65)
        self.assertEqual(result["error"],["TIMEOUT"])
        self.assertFalse(result["done"])

    def test_http_failure(self):
        result=self.run_embed(["HTTP_503"])
        self.assertEqual(result["error"],["HTTP_503"])

    def test_invalid_response_rejected(self):
        for value in ("INVALID_VECTORS","INVALID_COUNT","BAD_JSON"):
            with self.subTest(value=value):
                result=self.run_embed([value])
                self.assertEqual(result["error"],["INVALID_EMBEDDINGS"])
                self.assertFalse(result["done"])

    def test_gui_semantic_completion_and_cancel(self):
        from fusion.tokenlab_dialog import TokenLabDialog
        dialog=TokenLabDialog()
        try:
            ui=dialog.workspace
            ui.embed_stream.server=self.url
            ui.semantic.setChecked(True)
            ui.dup_lines.setPlainText("Igual\nIgual\nDistinto")
            ui.run_dedup()
            self.assertTrue(ui.embed_stream.active)
            self.assertFalse(ui.dedup_button.isEnabled())
            deadline=time.monotonic()+3
            while ui.embed_stream.active and time.monotonic()<deadline:
                self.app.processEvents()
                time.sleep(.004)
            self.assertEqual(ui.dup_result.toPlainText().splitlines(),["Igual","Distinto"])
            self.assertTrue(ui.dedup_button.isEnabled())
            old=ui.dup_result.toPlainText()
            ui.dup_lines.setPlainText("WAIT_FOR_CANCEL")
            ui.run_dedup()
            ui.embed_stream.cancel()
            deadline=time.monotonic()+3
            while ui.embed_stream.active and time.monotonic()<deadline:
                self.app.processEvents()
                time.sleep(.004)
            self.app.processEvents()
            self.assertEqual(ui.dup_result.toPlainText(),old)
            self.assertIn("CANCELADO",ui.dup_status.text())
            self.assertTrue(ui.dedup_button.isEnabled())
        finally:
            if dialog.workspace.embed_stream.active:
                dialog.workspace.embed_stream.cancel()
            dialog.close()

    def test_input_validation(self):
        worker=OllamaEmbeddings(server=self.url)
        for value in ([],[""],["x"]*129,["x"*10001]):
            with self.assertRaises(ValueError):
                worker.start(value)

if __name__=="__main__":
    unittest.main()
