"""Unit tests for the optional REA adapter; no npm install or REA required."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fusion import rea_bridge
from fusion.integrations import export_mcp_client_config, scan


class REABridgeTests(unittest.TestCase):
    def test_find_rea_missing(self):
        with patch("fusion.rea_bridge.shutil.which", return_value=None):
            with self.assertRaises(FileNotFoundError):
                rea_bridge.find_rea()

    def test_doctor_uses_structured_cli_and_json(self):
        payload = {"ready": True, "providers": []}
        with patch("fusion.rea_bridge.subprocess.run", return_value=SimpleNamespace(
            returncode=0, stdout=json.dumps(payload), stderr="",
        )) as run:
            self.assertEqual(rea_bridge.doctor(executable=sys.executable), payload)
        args = run.call_args.args[0]
        self.assertEqual(args[1:], ["doctor", "--json"])
        self.assertFalse(run.call_args.kwargs["shell"])

    def test_analyze_local_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("fusion.rea_bridge.subprocess.run", return_value=SimpleNamespace(
                returncode=0, stdout='{"evidence":[]}', stderr="",
            )) as run:
                result = rea_bridge.analyze_javascript_application(folder, executable=sys.executable)
            self.assertEqual(result, {"evidence": []})
            self.assertEqual(run.call_args.args[0][1:3], ["analyze-javascript-application", str(Path(folder).resolve())])

    def test_reject_unrelated_file_without_executing(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "file.exe"
            target.write_bytes(b"dummy")
            with patch("fusion.rea_bridge.subprocess.run") as run:
                with self.assertRaises(ValueError):
                    rea_bridge.analyze_javascript_application(target, executable=sys.executable)
                run.assert_not_called()

    def test_errors_are_not_success(self):
        with patch("fusion.rea_bridge.subprocess.run", return_value=SimpleNamespace(
            returncode=1, stdout="", stderr="not ready",
        )):
            with self.assertRaisesRegex(rea_bridge.REAError, "not ready"):
                rea_bridge.doctor(executable=sys.executable)
        with patch("fusion.rea_bridge.subprocess.run", return_value=SimpleNamespace(
            returncode=0, stdout="not json", stderr="",
        )):
            with self.assertRaisesRegex(rea_bridge.REAError, "JSON válido"):
                rea_bridge.doctor(executable=sys.executable)

    def test_timeout(self):
        import subprocess
        with patch("fusion.rea_bridge.subprocess.run", side_effect=subprocess.TimeoutExpired("rea", 2)):
            with self.assertRaises(rea_bridge.REAError):
                rea_bridge.doctor(executable=sys.executable, timeout=2)

    def test_optional_mcp_registration_and_scan(self):
        with tempfile.TemporaryDirectory() as folder:
            cli = Path(folder) / "rea"
            cli.write_text("local binary stub", encoding="utf-8")
            destination = Path(folder) / "mcp.json"
            config = {"rea_cli": str(cli)}
            self.assertTrue(scan(config)["REA"]["found"])
            names = export_mcp_client_config(destination, config)
            self.assertIn("rea", names)
            payload = json.loads(destination.read_text(encoding="utf-8"))
            self.assertEqual(payload["mcpServers"]["rea"], {
                "command": str(cli.resolve()), "args": ["mcp"],
            })


if __name__ == "__main__":
    unittest.main()
