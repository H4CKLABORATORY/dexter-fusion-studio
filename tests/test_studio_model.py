"""Real export and non-destructive editing checks for the Qt studio model."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from fusion.project import create_project,read_json
from fusion.engine import export_plan
from fusion.phase2 import apply_timeline
from fusion.studio_model import StudioDocument


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg required')
class StudioDocumentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        root=Path(self.tmp.name)
        self.source=root/'original.mp4'
        subprocess.run([
            'ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
            '-f','lavfi','-i','testsrc2=size=320x180:rate=12',
            '-f','lavfi','-i','sine=frequency=220:sample_rate=48000',
            '-t','3.0','-c:v','mpeg4','-c:a','aac',str(self.source)
        ],check=True)
        folder,_=create_project(root/'workspace','Studio profesional',str(self.source),
                                 profile='freefire_short',platform='youtube')
        self.folder=folder
        self.document=StudioDocument(folder)

    def tearDown(self):
        self.tmp.cleanup()

    def test_trim_split_reorder_undo_and_no_source_mutation(self):
        original=self.source.read_bytes()
        d=self.document
        self.assertEqual(len(d.clips),1)
        d.split(0,1.0)
        self.assertEqual(len(d.clips),2)
        self.assertAlmostEqual(d.output_duration,3.0,delta=.05)
        d.move(0,1)
        self.assertEqual(d.clips[0].start,1.0)
        d.set_effect(0,effect='vhs',zoom=1.2)
        self.assertTrue(d.undo())
        self.assertEqual(d.clips[0].effect,'hype')
        self.assertTrue(d.redo())
        self.assertEqual(d.clips[0].effect,'vhs')
        saved=d.save()
        self.assertTrue(saved.is_file())
        self.assertEqual(len(read_json(saved)['clips']),2)
        self.assertEqual(self.source.read_bytes(),original)

    def test_invalid_trim_reverted(self):
        d=self.document
        with self.assertRaises(ValueError):
            d.trim(0,start=5)
        self.assertEqual(d.clips[0].start,0)

    def test_render_reordered_segments(self):
        d=self.document
        d.split(0,1.1)
        d.move(0,1)
        d.set_effect(0,effect='clean')
        d.set_effect(1,effect='clean')
        d.save()
        plan=apply_timeline(self.folder,overwrite=True)
        self.assertGreater(plan['clips'][0][0],plan['clips'][1][0])
        output=export_plan(self.folder,overwrite=False)
        self.assertTrue(output.exists())
        self.assertGreater(output.stat().st_size,4000)
