"""No-network safety and behavior tests for the user's Qwen local bridge."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.hermes import local_bridge as local


MODEL = "qwen3.8-27b-defiance-uncensored-mtp"


class BridgeTests(unittest.TestCase):
    def test_all_endpoints_loopback_only(self):
        self.assertEqual(set(local.ENDPOINTS), {"locally-uncensored", "lmstudio", "ollama"})
        for base, _ in local.ENDPOINTS.values():
            self.assertTrue(base.startswith("http://127.0.0.1:"))
            self.assertTrue(base.endswith("/v1"))

    def test_qwen_only(self):
        self.assertTrue(local._supports(MODEL))
        self.assertFalse(local._supports("llama3.2"))
        self.assertFalse(local._supports(None))

    @patch.object(local, "_request")
    def test_models_are_filtered(self, request):
        request.return_value = {"data": [{"id": MODEL}, {"id": "other-model"},
                                         {"id": MODEL}, {"oops": "missing id"}]}
        self.assertEqual(local.available_qwen("lmstudio"), [MODEL])
        request.assert_called_once_with("lmstudio", "/models", timeout=10)

    @patch.object(local, "_request")
    def test_sends_spanish_system_context_without_execution(self, request):
        request.side_effect = [
            {"data": [{"id": MODEL}]},
            {"choices": [{"message": {"content": "Sí, comprobado."}}]},
        ]
        self.assertEqual(local.chat("lmstudio", MODEL, "Hola", "Mi proyecto local"), "Sí, comprobado.")
        endpoint, path, payload = request.call_args.args
        self.assertEqual((endpoint, path), ("lmstudio", "/chat/completions"))
        self.assertEqual(payload["model"], MODEL)
        self.assertEqual(payload["stream"], False)
        self.assertIn("español latinoamericano", payload["messages"][0]["content"])
        self.assertIn("Mi proyecto local", payload["messages"][0]["content"])

    @patch.object(local, "_request")
    def test_reject_other_models_without_contact(self, request):
        with self.assertRaises(local.BridgeError):
            local.chat("lmstudio", "wrong-model", "hola")
        request.assert_not_called()

    @patch.object(local, "_request")
    def test_reject_model_not_loaded(self, request):
        request.return_value = {"data": []}
        with self.assertRaisesRegex(local.BridgeError, "no aparece"):
            local.chat("lmstudio", MODEL, "hola")

    def test_lu_requires_local_token(self):
        with patch.dict("os.environ", {"HERMES_LU_API_TOKEN": ""}):
            with self.assertRaisesRegex(local.BridgeError, "HERMES_LU_API_TOKEN"):
                local._request("locally-uncensored", "/models")

    def test_unknown_engine_does_not_contact_network(self):
        with self.assertRaises(local.BridgeError):
            local._request("remote-provider", "/models")

    @patch.object(local, "_request")
    def test_missing_output_rejected(self, request):
        request.side_effect = [{"data": [{"id": MODEL}]}, {"choices": []}]
        with self.assertRaises(local.BridgeError):
            local.chat("lmstudio", MODEL, "hola")

    def test_memory_file_requires_small_local_doc(self):
        with tempfile.TemporaryDirectory() as td:
            filename = Path(td, "memory.md")
            filename.write_text("Preferir español", encoding="utf-8")
            self.assertEqual(local.load_local_context(filename), "Preferir español")
            filename.write_text("x" * 14000, encoding="utf-8")
            with self.assertRaises(local.BridgeError):
                local.load_local_context(filename)

    @patch.object(local, "available_qwen", return_value=[MODEL])
    def test_cli_lists_without_model_downloads(self, models):
        with patch("builtins.print") as printer:
            self.assertEqual(local.main(["--engine", "lmstudio", "--list-models"]), 0)
        result = json.loads(printer.call_args.args[0])
        self.assertEqual(result["models"], [MODEL])

    def test_absent_model_required_for_chat(self):
        with self.assertRaises(local.BridgeError):
            local.chat("lmstudio", MODEL, "")


if __name__ == "__main__":
    unittest.main()
