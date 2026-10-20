"""Scheduler manifest and continuity tests (no model or network required)."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "hermes"))
import checkpoint as cp
import runner
import scheduler


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        def git(*args):
            subprocess.run(["git", *args], cwd=self.repo, capture_output=True,
                           text=True, check=True)
        git("init", "-q")
        git("checkout", "-qb", "feature/scheduled")
        git("config", "user.email", "test@example.invalid")
        git("config", "user.name", "Hermes Test")
        cp.save(cp.file_for(self.repo, "ready"),
                cp.new("project", "ready", "Do one safe step", "feature/scheduled", "Add test"))
        cp.save(cp.file_for(self.repo, "done"),
                cp.advance(cp.new("project", "done", "Fixed", "feature/scheduled", "Finish"),
                           status="completed", next_action="No pending tasks"))
        git("add", ".")
        git("commit", "-qm", "fixture")
        self.config = self.base / "projects.json"
        self.config.write_text(json.dumps({
            "schema_version": 1,
            "projects": [{"root": str(self.repo), "tasks": ["ready", "done"]}]
        }), encoding="utf-8")

    def test_status_cycle_skips_finished_and_reports_ready(self):
        result = scheduler.cycle(self.config, execute=False, max_runs=1)
        self.assertEqual(result["attempted"], 0)
        self.assertEqual(result["tasks"][0]["result"], "ready")
        self.assertEqual(result["tasks"][1]["result"], "skipped")

    def test_manifest_must_reject_duplicates(self):
        obj = json.loads(self.config.read_text())
        obj["projects"][0]["tasks"].append("ready")
        self.config.write_text(json.dumps(obj))
        with self.assertRaisesRegex(runner.RunnerError, "duplicada"):
            scheduler.read_manifest(self.config)

    def test_manifest_blocks_bad_task_paths(self):
        obj = json.loads(self.config.read_text())
        obj["projects"][0]["tasks"] = ["../../secrets"]
        self.config.write_text(json.dumps(obj))
        with self.assertRaises(ValueError):
            scheduler.read_manifest(self.config)

    def test_manifest_no_nonexistent_directory(self):
        obj = json.loads(self.config.read_text())
        obj["projects"][0]["root"] = str(self.base / "missing")
        self.config.write_text(json.dumps(obj))
        with self.assertRaisesRegex(runner.RunnerError, "inexistente"):
            scheduler.read_manifest(self.config)

    def test_execution_requires_both_opt_ins(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(scheduler.main(["--config", str(self.config), "--execute"]), 2)

    def test_max_tasks_bounded(self):
        with self.assertRaisesRegex(runner.RunnerError, "max-runs"):
            scheduler.cycle(self.config, execute=False, max_runs=100)


if __name__ == "__main__":
    unittest.main()
