import hashlib
import tempfile
import unittest
from pathlib import Path
from app_rebuilder.core import inspect_file

class TestInspect(unittest.TestCase):
    def test_pe_signature_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.bin"
            data = b"MZ" + b"test"
            path.write_bytes(data)
            result = inspect_file(path)
            self.assertEqual(result["format"], "PE (Windows, probable)")
            self.assertEqual(result["sha256"], hashlib.sha256(data).hexdigest())

    def test_missing(self):
        with self.assertRaises(ValueError):
            inspect_file("nonexistent-file-for-test-123")
