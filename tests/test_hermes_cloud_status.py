"""Read-only GitHub cloud monitor tests."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "hermes"))
import checkpoint as cp
import cloud_status


class CloudStatusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        self.outside = Path(self.tmp.name) / "outside" / "status.json"
        p = subprocess.run(["git", "init", "-q", str(self.root)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        cp.save(cp.file_for(self.root, "task-a"),
                cp.new("H4CKLABORATORY/demo", "task-a", "Audit", "main", "Add regression tests"))

    def test_empty_or_missing_checkpoint_fails_closed(self):
        with self.assertRaises(RuntimeError):
            cloud_status.make_report(Path(self.tmp.name), "a"*40)

    def test_report_returns_next_step_and_freshness(self):
        result = cloud_status.make_report(self.root, "b"*40)
        self.assertEqual(result["total"], 1)
        self.assertTrue(result["does_not_execute_ai"])
        self.assertEqual(result["tasks"][0]["next_action"], "Add regression tests")
        self.assertEqual(result["tasks"][0]["status"], "planned")

    def test_detects_incremental_review_for_outdated_sha(self):
        f = cp.file_for(self.root, "task-a")
        obj = cp.load(f)
        obj["last_observed_commit"] = "a"*40
        cp.save(f, obj)
        x = cloud_status.make_report(self.root, "b"*40)
        self.assertTrue(x["tasks"][0]["incremental_review_required"])
        self.assertTrue(x["tasks"][0]["verification_pending"])

    def test_refuses_corrupt_checkpoint(self):
        cp.file_for(self.root, "task-a").write_text('{"bad": "record"}')
        with self.assertRaises(ValueError):
            cloud_status.make_report(self.root, "a"*40)

    def test_output_cannot_be_written_to_git_tree(self):
        result = cloud_status.main(["--root", str(self.root),
                                    "--output", str(self.root / "report.json")])
        self.assertEqual(result, 2)
        self.assertFalse((self.root/"report.json").exists())

    def test_cli_report_written_only_outside_workspace(self):
        # Real git needs an initial commit, but passing head explicitly is tested above.
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Hermes Test"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "checkpoint baseline"], cwd=self.root, check=True)
        self.assertEqual(cloud_status.main(["--root", str(self.root),
                                           "--output", str(self.outside)]), 0)
        report = json.loads(self.outside.read_text())
        self.assertEqual(report["total"], 1)
        self.assertEqual(report["head"], cloud_status.git_head(self.root))


if __name__ == "__main__":
    unittest.main()
