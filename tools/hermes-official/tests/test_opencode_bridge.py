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

    def test_gstack_skill_lookup_matches_official_opencode_install(self):
        target = self.base / ".config" / "opencode" / "skills" / "gstack-review"
        target.mkdir(parents=True)
        (target / "SKILL.md").write_text("# Review")
        self.assertEqual(bridge.gstack_skill_path("review", home=self.base), target / "SKILL.md")
        with self.assertRaises(ValueError):
            bridge.gstack_skill_path("made-up", home=self.base)

    def test_gstack_selected_profile_passed_to_real_opencode_dispatch(self):
        bridge.enqueue(self.home, self.project, "Fix bug", "gstack-1", gstack="review")
        seen = []
        def executor(argv, cwd, log, timeout):
            seen.append(argv)
            (cwd / "fix.txt").write_text("change")
            return 0
        fake_skill = self.base / ".config" / "opencode" / "skills" / "gstack-review" / "SKILL.md"
        with patch.object(bridge, "gstack_skill_path", return_value=fake_skill):
            with patch.object(bridge.shutil, "which", return_value="/mock/opencode"):
                with patch.object(bridge, "execute", side_effect=executor):
                    self.assertEqual(bridge.run_one(self.home), 0)
        self.assertIn("gstack-review", seen[0][-1])
        self.assertIn("CHECKPOINT-DEXTER.md", seen[0][-1])
        task = bridge.read(self.home)["tasks"][0]
        self.assertEqual(task["gstack"], "review")
        self.assertEqual(task["status"], "needs_review")

    def test_missing_gstack_blocks_once_without_infinite_retries(self):
        bridge.enqueue(self.home, self.project, "Fix bug", "gstack-2", gstack="qa")
        with patch.object(bridge, "gstack_skill_path",
                          side_effect=FileNotFoundError("Install upstream gstack first")):
            with patch.object(bridge.shutil, "which", return_value="/mock/opencode"):
                with patch.object(bridge, "execute") as execute:
                    self.assertEqual(bridge.run_one(self.home), 2)
                    self.assertEqual(bridge.run_one(self.home), 0)
                    execute.assert_not_called()
        self.assertEqual(bridge.read(self.home)["tasks"][0]["status"], "blocked")

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
        # The reusable lock file remains after release; verify the OS lock is free.
        holder = bridge.acquire_lock(self.home)
        self.assertIsNotNone(holder)
        bridge.release_lock(holder)
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
        self.assertEqual(bridge.run_one(self.home), 0)
        task = bridge.read(self.home)["tasks"][0]
        self.assertEqual(task["status"], "blocked")
        self.assertIn("Interrupted", task["error"])

    def test_lock_blocks_concurrent_worker(self):
        holder = bridge.acquire_lock(self.home)
        self.assertIsNotNone(holder)
        try:
            self.assertEqual(bridge.run_one(self.home), 3)
            with self.assertRaisesRegex(RuntimeError, "busy"):
                bridge.enqueue(self.home, self.project, "cannot queue while busy", "locked")
        finally:
            bridge.release_lock(holder)
        self.assertEqual(bridge.enqueue(self.home, self.project, "can queue now", "unlocked"), "unlocked")

    def test_old_lock_file_no_longer_disables_dispatcher_forever(self):
        self.home.mkdir()
        (self.home / "runner.lock").write_bytes(b"stale")
        self.assertEqual(bridge.run_one(self.home), 0)
        self.assertEqual(bridge.enqueue(self.home, self.project, "still runs", "next"), "next")

    def test_interrupted_task_is_not_replayed_and_other_queued_task_starts(self):
        bridge.enqueue(self.home, self.project, "old", "old-task")
        bridge.enqueue(self.home, self.project, "next", "next-task")
        state = bridge.read(self.home)
        state["tasks"][0]["status"] = "running"
        bridge.write(self.home / "tasks.json", state)

        def make_file(argv, cwd, log, timeout):
            (cwd / "new.txt").write_text("task two was attempted")
            return 0

        with patch.object(bridge.shutil, "which", return_value="/mock/opencode"):
            with patch.object(bridge, "execute", side_effect=make_file) as execute:
                self.assertEqual(bridge.run_one(self.home), 0)
                self.assertEqual(execute.call_count, 1)
        done = bridge.read(self.home)["tasks"]
        self.assertEqual(done[0]["status"], "blocked")
        self.assertEqual(done[1]["status"], "needs_review")

if __name__ == "__main__":
    unittest.main()
