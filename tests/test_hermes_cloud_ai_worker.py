"""Unit tests for CPU-only agent worker, without executing untrusted code."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "hermes"))
import cloud_ai_worker as ai

SOURCE = '''def summarize_checkpoint(record: dict) -> dict:
    """Summarize a checkpoint, validating its structure."""
    if not isinstance(record, dict):
        raise ValueError("Bad checkpoint")
    return {"task_id": record.get("task_id"),
            "status": record.get("status"),
            "next_action": record.get("next_action")}
'''


class CloudAiWorkerTests(unittest.TestCase):
    def test_only_allowlisted_tasks(self):
        with self.assertRaises(ai.CloudWorkerError):
            ai.get_task("../../secrets")
        with self.assertRaises(ai.CloudWorkerError):
            ai.get_task("some-other-task")

    def test_dry_run_never_uses_model(self):
        with patch.object(ai.urllib.request, "urlopen", side_effect=AssertionError("no network")):
            self.assertEqual(ai.main(["--task-id", "checkpoint-summary-helper"]), 0)

    def test_valid_python_proposal(self):
        result = ai.validate_code(SOURCE)
        self.assertIn("summarize_checkpoint", result)

    def test_invalid_python_is_rejected(self):
        with self.assertRaises(ai.CloudWorkerError):
            ai.validate_code("def f(:\n  pass\n"*15)

    def test_module_side_effects_forbidden(self):
        for code in ("import os\n" + SOURCE,
                     "print('hello')\n" + SOURCE,
                     "def f():\n    exec('print(1)')\n"+SOURCE,
                     "def f():\n    return (1).__class__\n"+SOURCE):
            with self.subTest(code=code[:30]), self.assertRaises(ai.CloudWorkerError):
                ai.validate_code(code)

    def test_public_model_disabled_by_default(self):
        with patch.dict(ai.os.environ, {}, clear=True):
            with self.assertRaisesRegex(ai.CloudWorkerError, "deshabilitado"):
                ai.ollama_proposal("checkpoint-summary-helper")

    def test_mock_ollama_parses_json(self):
        response = json.dumps({"message": {"content": json.dumps({"code": SOURCE})}}).encode()
        fake_response = MagicMock()
        fake_response.read.return_value = response
        fake_response.__enter__.return_value = fake_response
        with patch.dict(ai.os.environ, {"HERMES_CLOUD_MODEL_ENABLED": "1"}):
            with patch.object(ai.urllib.request, "urlopen", return_value=fake_response) as remote:
                out = ai.ollama_proposal("checkpoint-summary-helper")
        self.assertEqual(out, SOURCE)
        self.assertEqual(remote.call_args.kwargs["timeout"], 360)

    def test_atomic_like_artifact_and_hash(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "proposed"
            info = ai.write_proposal("checkpoint-summary-helper", SOURCE, out)
            self.assertEqual(info["target"], "tools/hermes/experiments/checkpoint_summary.py")
            self.assertEqual(info["sha256"], hashlib.sha256(SOURCE.encode()).hexdigest())
            self.assertEqual((out / "proposal.py").read_text(), SOURCE)
            with self.assertRaises(ai.CloudWorkerError):
                ai.write_proposal("checkpoint-summary-helper", SOURCE, out)

    def test_no_generated_code_execution(self):
        malicious = '''def harmless(record):
    """This is an example of an attribute based forbidden call."""
    return record.system("echo fail")
'''
        with self.assertRaises(ai.CloudWorkerError):
            ai.validate_code(malicious)

    def test_invalid_response_json(self):
        response = json.dumps({"message": {"content": "no json"}}).encode()
        fake_response = MagicMock()
        fake_response.read.return_value = response
        fake_response.__enter__.return_value = fake_response
        with patch.dict(ai.os.environ, {"HERMES_CLOUD_MODEL_ENABLED": "1"}):
            with patch.object(ai.urllib.request, "urlopen", return_value=fake_response):
                with self.assertRaisesRegex(ai.CloudWorkerError, "JSON/code"):
                    ai.ollama_proposal("checkpoint-summary-helper")


if __name__ == "__main__":
    unittest.main()
