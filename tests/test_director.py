"""Tests for native local motion graphics and edit-reference rhythm."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from fusion.director import parse_prompt, render_motion, reference_cuts, reference_to_timeline
from fusion.project import create_project
from fusion.media import probe


class MotionPromptTests(unittest.TestCase):
    def test_spanish_prompt(self):
        item=parse_prompt('Haz una intro cinematográfica verde con texto «DEXTER FF» de 3 segundos')
        self.assertEqual(item['title'],'DEXTER FF')
        self.assertEqual(item['style'],'cinematic')
        self.assertEqual(item['palette'],'green')
        self.assertEqual(item['duration'],3)
        self.assertEqual(item['platform'],'shorts')

    def test_aspect_and_palette(self):
        item=parse_prompt('Animación roja horizontal con texto "TOKYO MANJI"')
        self.assertEqual((item['palette'],item['platform']),('red','youtube'))
        self.assertEqual(item['title'],'TOKYO MANJI')

    def test_reject_invalid_inputs(self):
        for text in ('', ' '):
            with self.assertRaises(ValueError):
                parse_prompt(text)
        with self.assertRaises(ValueError):
            parse_prompt('intro de 25 segundos')
        with self.assertRaises(ValueError):
            parse_prompt('video',title='malo\\notro')
        with self.assertRaises(ValueError):
            parse_prompt('video',platform='instagram')

    def test_local_only(self):
        self.assertIn('Plantilla procedural',parse_prompt('intro')['limitations'])


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'Requires FFmpeg')
class MotionExportTests(unittest.TestCase):
    def test_motion_mp4_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'motion.mp4'
            spec=parse_prompt('Intro roja retro con texto "DEXTER FF" de 1 segundo')
            path=render_motion(spec,out,size=(320,568))
            self.assertEqual(path,out.resolve())
            self.assertTrue(out.with_suffix('.json').exists())
            self.assertTrue(probe(out)['audio'])
            self.assertAlmostEqual(probe(out)['duration'],1,delta=.1)
            with self.assertRaises(FileExistsError):
                render_motion(spec,out,size=(320,568))

    def test_reference_timeline_preserves_original(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            src=root/'source.mp4'
            ref=root/'reference.mp4'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
                '-f','lavfi','-i','testsrc2=s=320x240:r=15','-t','2.4',
                '-c:v','mpeg4','-q:v','7',str(src)],check=True)
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
                '-f','lavfi','-i','color=c=red:s=320x240:r=15:d=1.2',
                '-f','lavfi','-i','color=c=blue:s=320x240:r=15:d=1.2',
                '-filter_complex','[0:v][1:v]concat=n=2:v=1:a=0[v]',
                '-map','[v]','-c:v','mpeg4','-q:v','7',str(ref)],check=True)
            analysis=reference_cuts(ref)
            self.assertGreaterEqual(len(analysis['reference_intervals']),2)
            digest=hashlib.sha256(src.read_bytes()).hexdigest()
            folder,_=create_project(root/'projects','Prueba director',str(src),profile='freefire_short')
            timeline=reference_to_timeline(folder,ref,prompt='estilo retro')
            self.assertEqual(timeline['effects'],'vhs')
            self.assertGreaterEqual(len(timeline['clips']),2)
            self.assertEqual(hashlib.sha256(src.read_bytes()).hexdigest(),digest)
            with self.assertRaises(FileExistsError):
                reference_to_timeline(folder,ref,prompt='estilo retro')
