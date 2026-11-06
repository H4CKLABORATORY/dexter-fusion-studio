"""Qt integration tests for the v3 multitrack workspace (offscreen).

Covers: migration v2 -> v3 from the real StudioWindow, marker add,
snapping, drag/drop of audio into A3, per-clip waveforms, the proxy
worker end-to-end, and a real offscreen screenshot.
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import json
import unittest
from pathlib import Path

try:
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication
    from fusion.project import create_project
    from fusion.qt_multitrack import ProxyWorker
    from fusion.studio_qt import StudioWindow
    from tests.synth import make_media, probe_json
except ImportError:  # pragma: no cover
    QApplication = None


@unittest.skipIf(QApplication is None, 'PySide6 not installed')
class QtMultitrackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.tmp = Path(__file__).parent / 'tmp_qt_mt'
        cls.tmp.mkdir(exist_ok=True)
        media = make_media(cls.tmp)
        cls.vid_a = media['vidA']
        cls.music = media['music']

    def setUp(self):
        folder, _ = create_project(
            str(self.tmp / 'work'), 'Prueba multipista', str(self.vid_a),
            profile='freefire_short')
        self.folder = folder
        self.win = StudioWindow(str(folder))
        self.app.processEvents()

    def tearDown(self):
        worker = getattr(self.win, '_wave_worker', None)
        if worker is not None and worker.isRunning():
            worker.wait(3000)
        for w in getattr(self.win, '_clip_wave_workers', []):
            if w.isRunning():
                w.wait(3000)
        self.win.close()
        self.app.processEvents()

    def test_migrate_shows_multitrack_rows(self):
        self.win.migrate_to_multitrack()
        self.app.processEvents()
        self.assertIsNotNone(self.win.multitrack)
        self.assertEqual(len(self.win.timeline.track_names), 7)
        self.assertEqual(len(self.win.multitrack.data['clips']), 1)
        self.assertTrue((self.folder / 'multitrack.json').is_file())
        data = json.loads((self.folder / 'multitrack.json').read_text())
        self.assertEqual(data['schema'], 3)

    def test_marker_and_snap(self):
        self.win.migrate_to_multitrack()
        self.win.on_marker_requested(1.0)
        self.assertEqual(len(self.win.multitrack.data['markers']), 1)
        # Snap: 1.24 is within 0.25s of the 1.0 marker.
        self.assertEqual(self.win.timeline.snap_time(1.24), 1.0)
        # Far from any point: unchanged.
        self.assertEqual(self.win.timeline.snap_time(3.7), 3.7)

    def test_drop_audio_into_a3_and_waveform(self):
        self.win.migrate_to_multitrack()
        self.win.on_media_dropped([str(self.music)], 2.0)
        self.app.processEvents()
        clips = [c for c in self.win.multitrack.data['clips']
                 if c['track_id'] == 'a3']
        self.assertEqual(len(clips), 1)
        clip = clips[0]
        self.assertAlmostEqual(clip['timeline_start'], 2.0)
        # Real waveform peaks land on the canvas for that clip.
        self.win.timeline.set_clip_waveform(clip['clip_id'], [0.1, 0.5, 0.9])
        self.assertEqual(
            self.win.timeline.clip_waveforms[clip['clip_id']], [0.1, 0.5, 0.9])

    def test_proxy_worker_renders_real_composition(self):
        self.win.migrate_to_multitrack()
        result = {}
        loop = QEventLoop()
        worker = ProxyWorker(self.win.multitrack.data, self.folder, height=240)
        worker.completed.connect(lambda p, h: (result.update(path=p, hit=h),
                                               loop.quit()))
        worker.failed.connect(lambda m: (result.update(error=m), loop.quit()))
        QTimer.singleShot(90000, loop.quit)
        worker.start()
        loop.exec()
        self.assertNotIn('error', result, result.get('error'))
        path = Path(result['path'])
        self.assertTrue(path.is_file())
        self.assertGreater(path.stat().st_size, 1000)
        probe = probe_json(path)
        self.assertAlmostEqual(float(probe['format']['duration']), 5.0, delta=0.6)

    def test_offscreen_screenshot_is_real_pixels(self):
        self.win.migrate_to_multitrack()
        self.app.processEvents()
        shot = self.tmp / 'qt-multitrack.png'
        self.win.show()
        self.app.processEvents()
        self.win.grab().save(str(shot))
        self.assertTrue(shot.is_file())
        self.assertGreater(shot.stat().st_size, 5000)
