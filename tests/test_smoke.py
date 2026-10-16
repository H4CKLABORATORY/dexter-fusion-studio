import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest
from fusion.project import create_project,read_json,safe_write
from fusion.engine import generate_plan,export_plan
from fusion.media import probe

@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg/ffprobe required')
class SmokeTests(unittest.TestCase):
    def test_complete_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            inp=root/'source.mp4'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',
                            '-f','lavfi','-i','color=c=blue:s=240x136:r=12',
                            '-t','1.2','-an','-c:v','mpeg4','-q:v','5',str(inp)],check=True)
            work,config=create_project(str(root/'workspace'),'Free Fire PVP Short',str(inp),profile='freefire_short')
            config['effects']='hype'
            config['platform']='tiktok'
            config['maximum_length']=1.1
            config['cut_style']='fade'
            captions=work/'scripts'/'demo.srt'
            captions.write_text('1\n00:00:00,050 --> 00:00:00,900\n¡Bro, qué pasó!\n\n',encoding='utf-8')
            config['subtitle_file']=str(captions)
            safe_write(work/'project.json',config)
            plan=generate_plan(work,max_duration=1.1)
            self.assertEqual(len(plan['subtitles']),1)
            output=export_plan(work)
            media=probe(output)
            self.assertEqual((media['width'],media['height']),(1080,1920))
            self.assertTrue(media['audio'])
            self.assertGreater(output.stat().st_size,2000)
            self.assertGreater(media['duration'],0)
            self.assertTrue(inp.exists())
