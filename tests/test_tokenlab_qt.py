"""Focused native Qt integration test; no mocked tokenizer in Qt CI."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import tempfile
import unittest
from unittest.mock import patch

try:
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QApplication
    from fusion.studio_qt import StudioWindow
    from fusion.tokenlab_dialog import TokenLabDialog
    from fusion.tokenlab_tools import AtomicTaskCheckpoint
except ImportError:
    QApplication=None

@unittest.skipIf(QApplication is None,"PySide6 not installed (tested in dedicated Qt CI)")
class TokenLabQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def test_main_toolbar_opens_real_tokenlab_dialog(self):
        window=StudioWindow()
        try:
            buttons=[a.text() for a in window.findChildren(QAction)]
            self.assertTrue(any("TokenLab" in label for label in buttons))
            with patch.object(TokenLabDialog,"exec",return_value=0) as called:
                window.open_tokenlab()
                called.assert_called_once()
        finally:
            window.close()

    def test_dialog_counts_and_persists_checkpoint(self):
        dialog=TokenLabDialog()
        try:
            dialog.a.setPlainText("Hola 👋")
            dialog.b.setPlainText("Hola 👋 mundo")
            dialog.compare()
            self.assertIn("Diferencia:",dialog.result.text())
            self.assertNotIn("no disponible",dialog.result.text().lower())
            with tempfile.TemporaryDirectory() as root:
                dialog.storage=AtomicTaskCheckpoint(root)
                dialog.save()
                self.assertEqual(AtomicTaskCheckpoint(root).load("studio_ab")["a"],"Hola 👋")
        finally:
            dialog.close()
