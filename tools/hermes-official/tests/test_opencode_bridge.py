"""Git worktrees real; mocked OpenCode subprocess."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "dexter_opencode_tick.py"
spec = importlib.util.spec_from_file_location("dexter_worker", SCRIPT)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout

class BridgeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / "repo"
        self.project.mkdir()
        self.home = self.base / "state"
        git(self.project, "init", "-q")
        git(self.project, "config", "user.name", "Test Runner")
        git(self.project, "config", "user.email", "test@example.com")
        (self.project / "README.md").write_text("unchanged\n")
        git(self.project, "add", ".")
        git(self.project, "commit", "-m", "initial")

    def test_queue_and_duplicate(self):
        self.assertEqual(bridge.enqueue(self.home, self.project, "fix bug", "first"), "first")
        with self.assertRaises(ValueError):
            bridge.enqueue(self.home, self.project, "again", "first")
        self.assertEqual(bridge.read(self.home)["tasks"][0]["status"], "pending")

    def test_invalid_queue_rejected(self):
        with self.assertRaises(ValueError):
            bridge.enqueue(self.home, self.project, "", "empty")
        with self.assertRaises(ValueError):
            bridge.enqueue(self.home, self.project, "x", "bad", timeout=3)
        with self.assertRaises(ValueError):
            bridge.enqueue(self.home, self.project, "x", "bad", checks=[[""]])

    def test_real_worktree_success_without_modifying_original(self):
        bridge.enqueue(self.home, self.project, "Implement one fix", "task1",
                       checks=[["python", "-c", "print(123)"]])
        def fake(argv, cwd, log, timeout):
            if argv[0] != "python":
                self.assertEqual(argv[1:5], ["run", "--agent", "build", "--format"])
                (cwd / "file.py").write_text("print('ok')\n")
            return 0
        with patch.object(bridge.shutil, "which", return_value="/mock/opencode"):
            with patch.object(bridge, "execute", side_effect=fake):
                self.assertEqual(bridge.run_one(self.home), 0)
        task = bridge.read(self.home)["tasks"][0]
        self.assertEqual(task["status"], "completed")
        self.assertTrue((Path(task["worktree"]) / "file.py").exists())
        self.assertFalse((self.project / "file.py").exists())
        self.assertFalse((self.home / "runner.lock").exists())
        self.assertEqual(bridge.run_one(self.home), 0)

    def test_changes_without_tests_need_review(self):
        bridge.enqueue(self.home, self.project, "Make change", "task2")
        def fake(argv, cwd, log, timeout):
            (cwd / "new.txt").write_text("change")
            return 0
        with patch.object(bridge.shutil, "which", return_value="/mock/opencode"):
            with patch.object(bridge, "execute", side_effect=fake):
                self.assertEqual(bridge.run_one(self.home), 0)
        self.assertEqual(bridge.read(self.home)["tasks"][0]["status"], "needs_review")

    def test_no_changes_fail_closed(self):
        bridge.enqueue(self.home, self.project, "No changes", "task3")
        with patch.object(bridge.shutil, "which", return_value="/mock/opencode"):
            with patch.object(bridge, "execute", return_value=0):
                self.assertEqual(bridge.run_one(self.home), 2)
        self.assertEqual(bridge.read(self.home)["tasks"][0]["status"], "blocked")
        self.assertEqual(bridge.run_one(self.home), 0)

    def test_opencode_error_preserves_worktree(self):
        bridge.enqueue(self.home, self.project, "Try", "task4")
        with patch.object(bridge.shutil, "which", return_value="/mock/opencode"):
            with patch.object(bridge, "execute", return_value=7):
                self.assertEqual(bridge.run_one(self.home), 2)
        task = bridge.read(self.home)["tasks"][0]
        self.assertEqual(task["status"], "blocked")
        self.assertTrue(Path(task["worktree"]).is_dir())

    def test_interrupted_job_refuses_unverified_retry(self):
        bridge.enqueue(self.home, self.project, "Try", "task5")
        state = bridge.read(self.home)
        state["tasks"][0]["status"] = "running"
        bridge.write(self.home / "tasks.json", state)
        self.assertEqual(bridge.run_one(self.home), 4)

    def test_lock_blocks_concurrent_worker(self):
        self.home.mkdir()
        (self.home / "runner.lock").write_text("locked")
        self.assertEqual(bridge.run_one(self.home), 3)
        self.assertTrue((self.home / "runner.lock").exists())

if __name__ == "__main__":
    unittest.main()
