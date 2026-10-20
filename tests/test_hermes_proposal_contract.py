"""Tests for the unprivileged functional gate on AI proposal artifacts."""
from __future__ import annotations

import ast
from pathlib import Path
import json
import tempfile
import unittest

from tools.hermes import proposal_contract as gate

SOURCE = Path("tools/hermes/experiments/checkpoint_summary.py").read_text(encoding="utf-8")


class ProposalContractTests(unittest.TestCase):
    def test_reviewed_ollama_helper_satisfies_real_behavior(self):
        report = gate.check_source(SOURCE)
        self.assertTrue(report["passed"])
        self.assertGreaterEqual(report["checks"], gate.MIN_CONTRACT_CHECKS)
        self.assertEqual(report["policy"], "hermes-checkpoint-summary-v1")

    def test_original_model_logic_fails_behavior(self):
        broken = '''def summarize_checkpoint(record: dict) -> dict:
    """Draft model output, not yet correct."""
    if not isinstance(record, dict):
        raise ValueError("bad")
    return {
        "task_id": record["task_id"], "project": record["project"],
        "status": record["status"], "next_action": record["next_action"],
        "blockers_count": len(record["blockers"]),
        "verification_pending": record["last_verified_commit"] is None,
    }
'''
        with self.assertRaises(gate.ContractError):
            gate.check_source(broken)

    def test_reject_no_docstring(self):
        module = ast.parse(SOURCE)
        module.body[0].body.pop(0)
        no_doc = ast.unparse(module) + "\n"
        with self.assertRaisesRegex(gate.ContractError, "docstring"):
            gate.check_source(no_doc)

    def test_reject_unsafe_import(self):
        with self.assertRaisesRegex(gate.ContractError, "AST"):
            gate.check_source("import os\n" + SOURCE)

    def test_reject_infinite_loop(self):
        looping = '''def summarize_checkpoint(record: dict) -> dict:
    """Never returns."""
    while True:
        pass
'''
        with self.assertRaises(gate.ContractError):
            gate.check_source(looping, timeout_seconds=3)

    def test_error_on_invalid_timeout(self):
        with self.assertRaises(gate.ContractError):
            gate.check_source(SOURCE, timeout_seconds=500)

    def test_cli_creates_json_report_only_for_pass(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / "proposal.py"
            report = Path(d) / "functional.json"
            source.write_text(SOURCE, encoding="utf-8")
            self.assertEqual(gate.main(["--source", str(source), "--report", str(report)]), 0)
            obj = json.loads(report.read_text())
            self.assertTrue(obj["passed"])
            self.assertEqual(obj["sha256"], gate.check_source(SOURCE)["sha256"])
            report.unlink()
            source.write_text("import os\n" + SOURCE, encoding="utf-8")
            self.assertEqual(gate.main(["--source", str(source), "--report", str(report)]), 2)
            self.assertFalse(report.exists())


if __name__ == "__main__":
    unittest.main()
