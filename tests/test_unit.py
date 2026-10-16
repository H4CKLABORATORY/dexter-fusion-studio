import json
from pathlib import Path
import tempfile
import unittest
from fusion.project import safe_slug,detect_profile,create_project,seed_personal_knowledge,read_json
from fusion.media import keep_ranges,select_segments
from fusion.engine import read_srt,map_srt,write_srt,suggest_memes,validate_plan,EFFECTS
from fusion.library import import_scripts

class AppTests(unittest.TestCase):
    def test_name(self):
        self.assertEqual(safe_slug('Un video nuevo!'),'un-video-nuevo')
    def test_recognition(self):
        self.assertEqual(detect_profile('Video nuevo')['status'],'needs_input')
        self.assertEqual(detect_profile('Free Fire interesada en isla social')['profile'],'freefire_story')
    def test_ranges(self):
        self.assertEqual(keep_ranges(8,[[1,2],[3,5]],pad=0,min_keep=.75),[[0,1],[2,3],[5,8]])
        self.assertEqual(select_segments([[0,2],[4,8]],3),[[0,2],[4,5]])
    def test_srt(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'a.srt'
            path.write_text('1\n00:00:00,000 --> 00:00:01,500\nQué pasó bro\n\n2\n00:00:03,200 --> 00:00:03,700\nSorpresa\n',encoding='utf-8')
            r=map_srt(read_srt(path),[[0,2],[3,4]])
            self.assertAlmostEqual(r[1]['start'],2.2)
            write_srt(r,Path(tmp)/'b.srt')
            self.assertEqual(len(read_srt(Path(tmp)/'b.srt')),2)
    def test_memes_require_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'surprise.png';file.write_bytes(b'fake')
            events=suggest_memes([{'start':2,'end':3,'text':'sorpresa'}],[{'path':str(file),'tags':['sorpresa'],'approved':True}])
            self.assertEqual(len(events),1)
            self.assertFalse(events[0]['approved'])
    def test_script_import_dedup(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp);(r/'orig').mkdir()
            (r/'orig'/'guion.txt').write_text('Hola bro, qué pasó',encoding='utf-8')
            a=import_scripts(r/'workspace',r/'orig');b=import_scripts(r/'workspace',r/'orig')
            self.assertEqual(len(a['added']),1);self.assertEqual(b['duplicates'],1)
    def test_personal_style_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=seed_personal_knowledge(tmp)
            a.write_text('{"original":true}',encoding='utf-8')
            seed_personal_knowledge(tmp)
            self.assertTrue(read_json(a)['original'])
    def test_creation_does_not_copy_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);media=base/'test.mp4';media.write_bytes(b'not a real video')
            project,item=create_project(base/'work','Prueba',str(media),profile='freefire_short')
            # Windows can expand a TEMP short-path (RUNNER~1) on resolve().
            # Validate that both names reference the exact same source file.
            self.assertTrue(Path(item['source']).samefile(media))
            self.assertFalse((project/'input'/'test.mp4').exists())
            self.assertTrue((project/'project.json').is_file())
if __name__=='__main__':unittest.main()
