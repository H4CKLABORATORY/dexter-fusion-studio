"""GUI smoke test running with QT_QPA_PLATFORM=offscreen in CI."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')

import unittest
try:
    from PySide6.QtWidgets import QApplication
    from fusion.studio_qt import StudioWindow
except ImportError:
    QApplication=None
    StudioWindow=None


@unittest.skipIf(QApplication is None, 'PySide6 not installed')
class StudioQtSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def test_workspace_builds_and_shows_tracks(self):
        win=StudioWindow()
        win.show()
        self.app.processEvents()
        self.assertEqual(len(win.timeline.track_names),6)
        self.assertIn('DEXTER FUSION STUDIO',win.windowTitle())
        self.assertGreaterEqual(win.effects_list.count(),17)
        self.assertFalse(win.export_button.isEnabled())
        self.assertGreater(win.width(),1000)
        win.close()
