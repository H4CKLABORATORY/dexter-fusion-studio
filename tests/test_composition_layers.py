"""End-to-end V2 overlay and A3 music render tests.

Checks real output pixels and audio frequency, not just JSON or UI decoration.
"""
from __future__ import annotations

import math
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib

from fusion.composition_layers import validate_layers
from fusion.engine import export_plan
from fusion.media import probe
from fusion.phase2 import apply_timeline
from fusion.project import create_project,read_json
from fusion.studio_model import StudioDocument


def _png(path, color=(250, 25, 35), width=96, height=64):
    def chunk(name, data):
        return (struct.pack('>I',len(data))+name+data+
                struct.pack('>I',zlib.crc32(name+data)&0xffffffff))
    pixels=(bytes([0])+bytes([*color,255])*width)*height
    path.write_bytes(
        b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+
        chunk(b'IDAT',zlib.compress(pixels,9))+chunk(b'IEND',b'')
    )


def _run(args):
    return subprocess.run(args,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout


def _pixel(video,time):
    raw=_run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin',
        '-ss',str(time),'-i',str(video),'-vf',
        'crop=2:2:(iw-2)/2:(ih-2)/2,format=rgb24',
        '-frames:v','1','-f','rawvideo','pipe:1'])
    return raw[:3]


def _tone_energy(video,frequency):
    raw=_run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin',
        '-ss','0.7','-t','0.25','-i',str(video),'-vn','-ac','1','-ar','8000',
        '-f','s16le','pipe:1'])
    samples=struct.unpack('<'+'h'*(len(raw)//2),raw)
    n=len(samples)
    # Goertzel-like correlation for chosen sinusoid.
    sin=sum(v*math.sin(2*math.pi*frequency*i/8000) for i,v in enumerate(samples))
    cos=sum(v*math.cos(2*math.pi*frequency*i/8000) for i,v in enumerate(samples))
    return math.hypot(sin,cos)*2/max(1,n)/32768


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'Requires FFmpeg')
class LayerCompositionTests(unittest.TestCase):
    def setUp(self):
        self._dir=tempfile.TemporaryDirectory()
        root=Path(self._dir.name)
        self.source=root/'original.mp4'
        _run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
            '-f','lavfi','-i','color=c=blue:s=320x180:r=15:d=3',
            '-f','lavfi','-i','sine=frequency=220:sample_rate=48000:duration=3',
            '-c:v','mpeg4','-q:v','5','-c:a','aac','-shortest',str(self.source)])
        self.music=root/'background.wav'
        _run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
            '-f','lavfi','-i','sine=frequency=660:sample_rate=48000:duration=3',
            '-c:a','pcm_s16le',str(self.music)])
        self.image=root/'banner.png'
        _png(self.image)
        self.folder,_=create_project(root/'work','Real layer export',
            str(self.source),profile='freefire_short',platform='youtube')

    def tearDown(self):
        self._dir.cleanup()

    def test_real_v2_image_and_a3_music_render(self):
        doc=StudioDocument(self.folder)
        doc.add_image(str(self.image),start=1.0,end=2.5,width=.35,x=.5,y=.5)
        doc.add_audio(str(self.music),start=0,source_start=0,duration=2.8,gain=1.0)
        doc.save()
        self.assertEqual(len(read_json(self.folder/'timeline-v2.json')['layers']['audio']),1)
        plan=apply_timeline(self.folder,overwrite=True)
        self.assertEqual(len(plan['layers']['images']),1)
        output=export_plan(self.folder)
        self.assertTrue(output.exists())
        self.assertTrue(probe(output)['audio'])
        before=_pixel(output,.5)
        after=_pixel(output,1.7)
        self.assertGreater(before[2],before[0])
        self.assertGreater(after[0],after[2])
        self.assertGreater(_tone_energy(output,660),.02)
        self.assertGreater(_tone_energy(output,220),.02)

    def test_undo_and_invalid_layer_rejection(self):
        doc=StudioDocument(self.folder)
        doc.add_audio(str(self.music),gain=.3)
        self.assertEqual(len(doc.layers['audio']),1)
        self.assertTrue(doc.undo())
        self.assertEqual(len(doc.layers['audio']),0)
        self.assertTrue(doc.redo())
        self.assertEqual(len(doc.layers['audio']),1)
        with self.assertRaises(ValueError):
            doc.update_layer('audio',0,gain=999)
        self.assertEqual(doc.layers['audio'][0]['gain'],.3)
        with self.assertRaises(ValueError):
            doc.add_image(str(self.image),end=100)
        self.assertFalse(doc.layers['images'])
        with self.assertRaises(FileNotFoundError):
            validate_layers({'audio':[{'path':'missing.mp3'}]},3)

    def test_source_never_modified(self):
        original=self.source.read_bytes()
        doc=StudioDocument(self.folder)
        doc.add_image(str(self.image))
        doc.save()
        apply_timeline(self.folder,overwrite=True)
        export_plan(self.folder)
        self.assertEqual(self.source.read_bytes(),original)
