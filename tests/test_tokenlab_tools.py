"""Unit tests: official parity is required in CI, no mock tokenizer substituted."""
import tempfile
import unittest
from fusion.tokenlab_tools import compare_texts,exact_sha256,AtomicTaskCheckpoint,TokenLabUnavailable

class TokenLabIntegration(unittest.TestCase):
    def test_checkpoint_resume_after_interruption(self):
        with tempfile.TemporaryDirectory() as directory:
            first=AtomicTaskCheckpoint(directory)
            first.save("render_001",{"frame":45,"files":["a.mp4"],"done":False})
            resumed=AtomicTaskCheckpoint(directory)
            self.assertEqual(resumed.load("render_001")["frame"],45)
            first.save("render_001",{"frame":46,"done":True})
            self.assertTrue(resumed.load("render_001")["done"])
            self.assertIsNone(resumed.load("unknown"))

    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            cp=AtomicTaskCheckpoint(directory)
            with self.assertRaises(ValueError): cp.save("../outside",{"a":1})
            with self.assertRaises(ValueError): cp.load("a/b")

    def test_distinct_content_hash(self):
        self.assertEqual(exact_sha256("hola"),exact_sha256("hola"))
        self.assertNotEqual(exact_sha256("hola"),exact_sha256("hola!"))

    def test_parity_with_official_tokenizer(self):
        import tiktoken
        a="Hola 👋 DexTER"
        b="Hola Dexter y Free Fire\\nNueva línea"
        for model in ("gpt-4o","gpt-4.1"):
            enc=tiktoken.encoding_for_model(model)
            result=compare_texts(a,b,model)
            self.assertEqual(result["a_tokens"],len(enc.encode(a)))
            self.assertEqual(result["b_tokens"],len(enc.encode(b)))
            self.assertEqual(result["difference"],len(enc.encode(b))-len(enc.encode(a)))
            self.assertEqual(result["encoding"],enc.name)

    def test_type_rejection(self):
        with self.assertRaises(TypeError): compare_texts(None,"ok")

if __name__=="__main__":
    unittest.main()
