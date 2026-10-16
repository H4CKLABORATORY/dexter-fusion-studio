import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest
from fusion.project import create_project, safe_write, read_json
from fusion.phase2 import score_windows,select_nonoverlap,build_timeline,apply_timeline,validate_timeline
from fusion.engine import EFFECTS,export_plan
from fusion.media import probe

class Phase2HeuristicTests(unittest.TestCase):
    def test_score_is_explainable(self):
        subs=[{'start':3,'end':4,'text':'¡Bro, qué sorpresa!'}]
        scored=score_windows(24,[2,3.5,5],[[18,22]],subs,window=8,step=4)
        self.assertGreater(scored[0]['score'],0)
        self.assertIn('bro',scored[0]['keyword_evidence'])
        self.assertIn('reason',scored[0])
    def test_nonoverlap(self):
        source=[{'start':0,'end':8,'score':10},{'start':2,'end':10,'score':9},
                {'start':12,'end':20,'score':7}]
        self.assertEqual(len(select_nonoverlap(source)),2)
    def test_more_presets(self):
        for name in ('glitch','neon','vhs','comic','warm','night'):
            self.assertIn(name,EFFECTS)

@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'Requires local FFmpeg')
class Phase2SmokeTests(unittest.TestCase):
    def test_crossfade_per_clip_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            video=base/'source.mp4'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
                '-f','lavfi','-i','testsrc2=s=224x128:r=15', '-t','3.6',
                '-c:v','mpeg4','-q:v','5',str(video)],check=True)
            folder,config=create_project(base/'work','Free Fire botsito short',str(video),profile='freefire_short')
            config.update({'platform':'tiktok','effects':'neon','cut_style':'hard'})
            safe_write(folder/'project.json',config)
            timeline=build_timeline(folder,scan_seconds=3,select_highlights=False)
            self.assertEqual(len(timeline['clips']),1)
            timeline['clips']=[
                {'id':1,'start':0.,'end':1.7,'effect':'glitch','zoom':1.05,'label':'inicio'},
                {'id':2,'start':1.7,'end':3.5,'effect':'warm','zoom':1.0,'label':'final'}]
            timeline['cut_style']='crossfade';timeline['transition_seconds']=0.22
            safe_write(folder/'timeline-v2.json',timeline)
            validate_timeline(timeline)
            plan=apply_timeline(folder)
            self.assertEqual(plan['clip_effects'],['glitch','warm'])
            path=export_plan(folder)
            self.assertTrue(path.is_file())
            data=probe(path)
            self.assertEqual((data['width'],data['height']),(1080,1920))
            self.assertAlmostEqual(data['duration'],1.7+1.8-0.22,delta=.18)
            self.assertTrue(data['audio'])
