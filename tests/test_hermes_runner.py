"""Integration tests for the local Hermes one-shot runner."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "hermes"))
import checkpoint as cp
import runner


@unittest.skipUnless(sys.platform != "win32", "Tests use POSIX fake Hermes CLI; Windows uses actual CLI")
class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "repo"
        self.root.mkdir()
        def git(*a):
            p = subprocess.run(["git", *a], cwd=self.root, text=True, capture_output=True)
            if p.returncode:
                self.fail(f"git {a}: {p.stderr}")
        git("init", "-q")
        git("checkout", "-qb", "feature/hermes-test")
        git("config", "user.email", "hermes-test@example.invalid")
        git("config", "user.name", "Hermes Test")
        (self.root / "README.md").write_text("test repo\n", encoding="utf-8")
        seed = cp.new("H4CKLABORATORY/mock", "task-one",
                      "Corregir error X", "feature/hermes-test", "Implementar pequeña prueba")
        dest = cp.file_for(self.root, "task-one")
        cp.save(dest, seed)
        git("add", ".")
        git("commit", "-qm", "baseline")
        self.store = self.base / "private-checkpoints"
        self.fake = self.base / "hermes"
        self.fake.write_text("#!/usr/bin/env python3\nimport sys\nsys.stdin.read()\nprint('done')\n", encoding="utf-8")
        self.fake.chmod(0o700)

    def test_status_reads_template_without_writing(self):
        result = runner.one_tick(self.root, "task-one", str(self.fake), self.store,
                                 20, enabled=False, execute=False)
        self.assertEqual(result["mode"], "status")
        self.assertFalse(result["private_checkpoint"])
        self.assertEqual(result["workspace"]["branch"], "feature/hermes-test")
        self.assertFalse(cp.file_for(self.store, "task-one").exists())

    def test_run_requires_opt_in(self):
        with self.assertRaisesRegex(runner.RunnerError, "HERMES_RUN_ENABLED"):
            runner.one_tick(self.root, "task-one", str(self.fake), self.store,
                            20, enabled=False, execute=True)

    def test_success_persists_private_checkpoint_without_claiming_verification(self):
        output = runner.one_tick(self.root, "task-one", str(self.fake), self.store,
                                 20, enabled=True, execute=True)
        self.assertTrue(output["agent_completed"])
        payload = cp.load(cp.file_for(self.store, "task-one"))
        self.assertEqual(payload["status"], "blocked")
        self.assertIn("sin un commit nuevo", payload["next_action"])
        self.assertIsNone(payload["last_verified_commit"])
        self.assertEqual(payload["verification"][-1]["result"], "not_run")
        self.assertEqual(runner.run_git(self.root, "status", "--porcelain"), "")
        self.assertFalse((self.root / "secret.txt").exists())

    def test_successful_new_commit_keeps_task_active(self):
        # Fake one-shot agent performs a tiny authorized change and commits it.
        self.fake.write_text(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "import subprocess,sys\n"
            "sys.stdin.read()\n"
            "Path('generated.txt').write_text('done')\n"
            "subprocess.run(['git','add','generated.txt'],check=True)\n"
            "subprocess.run(['git','commit','-qm','test change'],check=True)\n"
            "print('done')\n", encoding="utf-8"
        )
        out = runner.one_tick(self.root, "task-one", str(self.fake), self.store,
                              20, enabled=True, execute=True)
        self.assertTrue(out["progress_detected"])
        self.assertEqual(out["state"], "in_progress")
        item = cp.load(cp.file_for(self.store, "task-one"))
        self.assertIsNone(item["last_verified_commit"])
        self.assertEqual(item["last_observed_commit"],
                         runner.run_git(self.root, "rev-parse", "HEAD"))

    def test_failure_blocks_restart_and_retains_checkpoint(self):
        self.fake.write_text("#!/usr/bin/env python3\nimport sys\nsys.exit(7)\n", encoding="utf-8")
        result = runner.one_tick(self.root, "task-one", str(self.fake), self.store,
                                 20, enabled=True, execute=True)
        self.assertEqual(result["exit_code"], 7)
        self.assertEqual(result["state"], "blocked")
        checkpoint = cp.load(cp.file_for(self.store, "task-one"))
        self.assertIn("bloqueo", checkpoint["next_action"])
        with self.assertRaisesRegex(runner.RunnerError, "bloqueada o completada"):
            runner.one_tick(self.root, "task-one", str(self.fake), self.store,
                            20, enabled=True, execute=True)

    def test_detects_main_protected(self):
        subprocess.run(["git", "checkout", "-qb", "main"], cwd=self.root,
                       capture_output=True, check=True)
        with self.assertRaisesRegex(runner.RunnerError, "main/master"):
            runner.one_tick(self.root, "task-one", str(self.fake), self.store,
                            20, enabled=True, execute=True)

    def test_dirty_worktree_rejected(self):
        (self.root / "untracked.txt").write_text("dirty")
        with self.assertRaisesRegex(runner.RunnerError, "sucio"):
            runner.inspect_repo(self.root, execution=True)

    def test_lock_blocks_concurrent_worker(self):
        with runner.task_lock(self.store, "task-one"):
            with self.assertRaisesRegex(runner.RunnerError, "bloqueo"):
                with runner.task_lock(self.store, "task-one"):
                    pass
        self.assertFalse((self.store / "locks" / "task-one.lock").exists())

    def test_private_state_cannot_be_inside_repo(self):
        with self.assertRaisesRegex(runner.RunnerError, "fuera del repositorio"):
            runner.state_root(self.root, self.root / ".hermes" / "private")

    def test_mismatched_branch_fails(self):
        payload = cp.load(cp.file_for(self.root, "task-one"))
        snap = runner.inspect_repo(self.root)
        snap["branch"] = "feature/other"
        with self.assertRaisesRegex(runner.RunnerError, "Rama distinta"):
            runner.prompt_for(payload, snap)

    def test_prompt_documents_guards(self):
        message = runner.prompt_for(cp.load(cp.file_for(self.root, "task-one")),
                                   runner.inspect_repo(self.root))
        self.assertIn("No ejecutes git push", message)
        self.assertIn("pruebas", message)
        self.assertNotIn("AUTORUN_API_TOKEN=", message)

    def test_no_local_model_reports_actionable_error(self):
        with self.assertRaisesRegex(runner.RunnerError, "Instala y configura"):
            runner.one_tick(self.root, "task-one", "impossible-hermes-cli-123",
                            self.store, 20, enabled=True, execute=True)


if __name__ == "__main__":
    unittest.main()
