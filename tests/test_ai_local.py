"""Pruebas de etapa 3: permisos, ausencia de llamadas a nube, clips y transcripción."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from fusion.ai_local import (
    capabilities, evenly_spaced, parse_visual_response, annotate_candidates,
    analyze, draft, approve_draft, transcribe_local
)
from fusion.project import create_project, read_json, safe_write
from fusion.media import probe


class LocalAiLogicTests(unittest.TestCase):
    def test_module_state_is_readonly(self):
        self.assertIn("ffmpeg", capabilities())
        self.assertFalse("api_key" in capabilities())

    def test_visual_json_validation_and_uncertainty(self):
        raw='{"cue":"action","interesting":true,"summary":"Posible cambio rápido"}'
        result=parse_visual_response(raw)
        self.assertEqual(result["cue"], "action")
        self.assertTrue(result["interesting"])
        self.assertTrue(result["uncertain"])
        self.assertEqual(parse_visual_response("texto no JSON")["cue"],"unknown")
        self.assertEqual(parse_visual_response('{"cue":"hack","interesting":1}')["cue"], "unknown")
        self.assertFalse(parse_visual_response('{"cue":"hack","interesting":1}')["interesting"])

    def test_sample_boundaries(self):
        self.assertEqual(evenly_spaced(15,2),[5.0,10.0])
        with self.assertRaises(ValueError):
            evenly_spaced(30,13)

    def test_visual_evidence_boost_is_capped(self):
        clips=[{"start":0,"end":12,"score":1,"keyword_evidence":[]}]
        observations=[{"time":1,"cue":"action","interesting":True,"summary":"X"} for _ in range(10)]
        result=annotate_candidates(clips,observations)
        self.assertEqual(result[0]["score"],3.0)
        self.assertIn("confidence_note",result[0])


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "La prueba audiovisual requiere FFmpeg")
class LocalAiWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base=Path(self.tmp.name)
        video=base/"fake-gameplay.mp4"
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
                        "-f","lavfi","-i","color=c=blue:s=160x90:r=12",
                        "-t","3","-c:v","mpeg4","-q:v","5",str(video)],check=True)
        self.folder,config=create_project(base/"workspace","Free Fire botsito",
                                          str(video),profile="freefire_short")
        self.config=config

    def test_local_only_default_and_draft_does_not_replace_timeline(self):
        timeline=self.folder/"timeline-v2.json"
        safe_write(timeline,{"my_real_edits":"keep"})
        with patch("fusion.ai_local.ask_local_ollama",side_effect=AssertionError("vision should not run")):
            with patch("fusion.ai_local.scene_changes",return_value=[1.0,2.0]):
                report=analyze(self.folder,vision=False,scan_seconds=10,window=2)
        self.assertEqual(report["vision_samples"],0)
        self.assertTrue((self.folder/"ai-analysis.json").is_file())
        self.assertEqual(read_json(timeline)["my_real_edits"],"keep")
        created=draft(self.folder,limit=2)
        self.assertGreaterEqual(created["clips"],1)
        self.assertEqual(read_json(timeline)["my_real_edits"],"keep")
        with self.assertRaises(FileExistsError):
            approve_draft(self.folder)
        approved=approve_draft(self.folder,overwrite=True)
        self.assertTrue(Path(approved["timeline"]).exists())
        self.assertEqual(read_json(self.folder/"timeline-v2.before-ai.json")["my_real_edits"],"keep")
        self.assertTrue(read_json(timeline)["review_required"])

    def test_mocked_whisper_transcription_writes_real_srt(self):
        # Create a NEW sample with audio to exercise the workflow without model downloads.
        audio=Path(self.tmp.name)/"voice.mp4"
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
                        "-f","lavfi","-i","color=c=blue:s=160x90:r=12",
                        "-f","lavfi","-i","sine=frequency=500:sample_rate=16000",
                        "-t","2","-c:v","mpeg4","-c:a","aac","-shortest",str(audio)],check=True)
        self.config["source"]=str(audio)
        safe_write(self.folder/"project.json",self.config)
        class Segment:
            start,end,text=0.1,1.6," Hola bro "
        class WhisperModel:
            def __init__(self,*a,**kw):
                pass
            def transcribe(self,*a,**kw):
                return iter([Segment()]),types.SimpleNamespace(language="es")
        with patch.dict(sys.modules,{"faster_whisper":types.SimpleNamespace(WhisperModel=WhisperModel)}):
            response=transcribe_local(self.folder,model="small")
        self.assertEqual(response["segments"],1)
        self.assertIn("Hola bro",Path(response["subtitle_file"]).read_text(encoding="utf-8"))
        with self.assertRaises(FileExistsError):
            with patch.dict(sys.modules,{"faster_whisper":types.SimpleNamespace(WhisperModel=WhisperModel)}):
                transcribe_local(self.folder)


if __name__=="__main__":
    unittest.main()
