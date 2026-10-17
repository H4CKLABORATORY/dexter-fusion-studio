"""Caption rendering: timing, sanitization, styles, and optional FFmpeg smoke."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from fusion.caption_styles import render_ass, safe_words, ass_clock, write_ass
from fusion.engine import OUTPUTS, generate_plan, export_plan
from fusion.media import probe
from fusion.project import create_project, safe_write
from unittest.mock import patch


class CaptionTests(unittest.TestCase):
    def test_escape_and_clock(self):
        self.assertEqual(
            safe_words(r'{\\pos(1,1)} hola <i>mundo</i>'),
            ['(//pos(1,1))', 'hola', 'mundo'],
        )
        self.assertEqual(ass_clock(61.51), '0:01:01.51')

    def test_layout_and_timing(self):
        subtitle = {'start': 1, 'end': 3,
                    'text': 'Un video gracioso con todos mis amigos'}
        output = render_ass([subtitle], width=1080, height=1920, style='punch')
        self.assertIn('PlayResY: 1920', output)
        self.assertIn('\\kf', output)
        self.assertIn('\\t(0,170', output)
        self.assertGreaterEqual(output.count('Dialogue:'), 2)
        self.assertIn('0:00:03.00', output)

    def test_no_ass_overrides_from_user_text(self):
        content = render_ass(
            [{'start': 0, 'end': 1,
              'text': r'{\\move(1,1,3,3)} Texto <i>peligroso</i>'}],
            width=1920, height=1080,
        )
        self.assertNotIn(r'{\\move', content)
        self.assertIn('Texto', content)

    def test_write_and_skip_invalid_time(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'captions.ass'
            count = write_ass([
                {'start': 2, 'end': 1, 'text': 'invalid'},
                {'start': 0, 'end': 1, 'text': 'Hola mundo'},
            ], target, width=1920, height=1080)
            self.assertEqual(count, 1)
            self.assertTrue(target.exists())

    def test_reject_invalid_style(self):
        with self.assertRaises(ValueError):
            render_ass([], width=1920, height=1080, style='classic')


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),
                     'Requires FFmpeg and FFprobe')
class CaptionExportTests(unittest.TestCase):
    def test_punch_style_export_mp4(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            video = folder / 'input.mp4'
            subprocess.run([
                'ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin',
                '-y', '-f', 'lavfi', '-i', 'color=c=black:s=320x180:r=24',
                '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000',
                '-t', '1.3', '-c:v', 'mpeg4', '-c:a', 'aac', str(video),
            ], check=True)
            srt = folder / 'voice.srt'
            srt.write_text(
                '1\n00:00:00,120 --> 00:00:01,150\n'
                'Hoy tenemos un video muy bueno\n',
                encoding='utf-8',
            )
            project_folder, config = create_project(
                folder / 'work', 'Caption smoke', str(video),
                profile='freefire_short', platform='youtube',
            )
            config.update(subtitle_file=str(srt), caption_style='punch',
                          effects='clean', maximum_length=0)
            safe_write(project_folder / 'project.json', config)
            with patch.dict(OUTPUTS, {'youtube': (480, 270)}):
                plan = generate_plan(project_folder)
                self.assertEqual(plan['caption_style'], 'punch')
                output = export_plan(project_folder)
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 1500)
            self.assertGreater(probe(output)['duration'], 1.1)


if __name__ == '__main__':
    unittest.main()
