"""Transaction tests for async context compaction; fake signals only, not inference."""
import os
import unittest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtCore import QObject, Signal
    from PySide6.QtWidgets import QApplication
    from fusion.tokenlab_context import GestorContexto
    from fusion.tokenlab_context_async import AsyncContextCompactor
except ImportError:
    QApplication=None


if QApplication is not None:
    class FakeStream(QObject):
        completed=Signal(str)
        failed=Signal(str)
        cancelled=Signal()
        def __init__(self):
            super().__init__()
            self.active=False
            self.request=None
        def start(self, text, mode, output_tokens):
            self.active=True
            self.request=text
        def cancel(self):
            self.active=False
            self.cancelled.emit()
        def finish(self, text):
            self.active=False
            self.completed.emit(text)
        def error(self):
            self.active=False
            self.failed.emit("HTTP_503")


@unittest.skipIf(QApplication is None,"PySide6 unavailable; tested in Qt CI")
class CompactorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def build(self):
        mgr=GestorContexto("FIXED RULE",512,reserva_respuesta=64)
        old=" ".join("old_"+str(i) for i in range(105))
        newer=" ".join("new_"+str(i) for i in range(105))
        mgr.add("user",old)
        stream=FakeStream()
        controller=AsyncContextCompactor(mgr,stream)
        return mgr,stream,controller,newer

    def test_complete_without_blocking_and_preserve_permanent(self):
        mgr,stream,c,newer=self.build()
        received=[]
        c.updated.connect(received.append)
        c.append("assistant",newer)
        self.assertTrue(c.busy)
        self.assertTrue(stream.active)
        self.assertEqual(len(mgr.ventana_volatil),1)
        stream.finish("old summary")
        self.assertFalse(c.busy)
        self.assertEqual(mgr.memoria_permanente,"FIXED RULE")
        self.assertEqual(mgr.resumen_sesion,"old summary")
        self.assertEqual(len(received),1)

    def test_cancel_rolls_back(self):
        mgr,stream,c,newer=self.build()
        before=mgr.export()
        c.append("assistant",newer)
        c.cancel()
        self.assertEqual(mgr.export(),before)
        self.assertFalse(c.busy)

    def test_http_error_rolls_back(self):
        mgr,stream,c,newer=self.build()
        before=mgr.export()
        c.append("assistant",newer)
        stream.error()
        self.assertEqual(mgr.export(),before)

    def test_protected_fact_not_dropped(self):
        mgr,stream,c,newer=self.build()
        mgr.hechos_obligatorios=["ZX-731"]
        before=mgr.export()
        problems=[]
        c.failed.connect(problems.append)
        c.append("assistant",newer)
        stream.finish("resumen sin identificador")
        self.assertEqual(mgr.export(),before)
        self.assertTrue(problems)
