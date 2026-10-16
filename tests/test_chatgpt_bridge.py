"""Pruebas para la conexión opcional de ChatGPT, sin claves ni llamadas reales."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from fusion.chatgpt_bridge import (decode_response, make_packet, validate_response,
    import_response, approve_response, api_suggest)
from fusion.project import create_project, read_json, safe_write


class ParserTests(unittest.TestCase):
    def test_accepts_json_and_code_fences(self):
        self.assertEqual(decode_response('{"clips":[]}'),{"clips":[]})
        marker=chr(96)*3
        self.assertEqual(decode_response(marker+'json\n{"clips":[]}\n'+marker),{"clips":[]})
        with self.assertRaises(ValueError):
            decode_response('["no"]')

    def test_paid_api_is_off_without_authorization(self):
        with self.assertRaises(PermissionError):
            api_suggest("/tmp/no-such-project")


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "Las pruebas de video requieren FFmpeg")
class BridgeProjectTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base=Path(tmp.name)
        source=base/"test-original.mp4"
        subprocess.run(["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y",
                        "-f","lavfi","-i","color=c=blue:s=160x90:r=12",
                        "-t","3","-c:v","mpeg4","-q:v","5",str(source)],check=True)
        self.folder,self.project=create_project(base/"work","Free Fire botsito",
                                                str(source),profile="freefire_short")

    def sample(self, **extra):
        from fusion.chatgpt_bridge import project_fingerprint
        from fusion.ai_local import source_info
        folder,project,src,info=source_info(self.folder)
        data={
            "project_fingerprint":project_fingerprint(folder,src,info["duration"]),
            "platform":"tiktok","cut_style":"hard","transition_seconds":0.25,
            "clips":[{"start":0,"end":2.4,"effect":"hype",
                      "zoom":1.1,"label":"Hook"}],
            "notes":["Posible introducción; revisión pendiente"],
        }
        data.update(extra)
        return data

    def test_packet_only_summary_and_no_key(self):
        result=make_packet(self.folder)
        data=read_json(result["packet_file"])
        text=json.dumps(data)
        self.assertIn("project_fingerprint",data)
        self.assertNotIn(self.project["source"],text)
        self.assertNotIn("OPENAI_API_KEY",text)
        self.assertFalse((self.folder/"chatgpt-proposed-timeline.json").exists())
        with self.assertRaises(FileExistsError):
            make_packet(self.folder)

    def test_reject_invalid_or_wrong_project(self):
        with self.assertRaises(ValueError):
            validate_response(self.folder,self.sample(project_fingerprint="wrong"))
        for field,value in (("effect","fake_effect"),("end",99),("zoom",9)):
            clip=dict(self.sample()["clips"][0]);clip[field]=value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_response(self.folder,self.sample(clips=[clip]))
        self.assertFalse((self.folder/"timeline-v2.json").exists())

    def test_import_is_draft_only_and_backup_on_approval(self):
        prev={"my_edits":"keep"}
        safe_write(self.folder/"timeline-v2.json",prev)
        path=self.folder/"from-chatgpt.json"
        safe_write(path,self.sample())
        result=import_response(self.folder,path)
        self.assertEqual(result["clips"],1)
        self.assertEqual(read_json(self.folder/"timeline-v2.json"),prev)
        with self.assertRaises(FileExistsError):
            approve_response(self.folder)
        done=approve_response(self.folder,overwrite=True)
        self.assertEqual(read_json(self.folder/"timeline-v2.before-chatgpt.json"),prev)
        self.assertEqual(read_json(done["timeline"])["clips"][0]["effect"],"hype")
        self.assertTrue(read_json(done["timeline"])["review_required"])

    def test_api_requires_key_and_only_sends_text(self):
        make_packet(self.folder)
        with patch.dict(os.environ,{"OPENAI_API_KEY":""}):
            with self.assertRaises(RuntimeError):
                api_suggest(self.folder,allow_paid_api=True)
        answer=json.dumps(self.sample())
        output={"output":[{"type":"message","content":[{"type":"output_text","text":answer}]}],
                "usage":{"input_tokens":20,"output_tokens":30}}
        class FakeResponse:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self,*args):return json.dumps(output).encode("utf-8")
        def fake_open(req,timeout):
            body=json.loads(req.data.decode("utf-8"))
            self.assertTrue(req.full_url.startswith("https://api.openai.com/"))
            self.assertEqual(body["store"],False)
            self.assertNotIn("data:image",json.dumps(body))
            self.assertNotIn(self.project["source"],json.dumps(body))
            return FakeResponse()
        with patch.dict(os.environ,{"OPENAI_API_KEY":"test-only-not-a-real-secret"}):
            with patch("fusion.chatgpt_bridge.request.urlopen",side_effect=fake_open) as mocked:
                response=api_suggest(self.folder,allow_paid_api=True)
        self.assertEqual(mocked.call_count,1)
        self.assertEqual(response["clips"],1)
        self.assertTrue((self.folder/"chatgpt-proposed-timeline.json").is_file())
        self.assertFalse((self.folder/"timeline-v2.json").exists())


if __name__=="__main__":
    unittest.main()
