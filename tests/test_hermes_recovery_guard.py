"""Regression tests for deterministic recovery guard."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "hermes"))
from recovery_guard import RecoveryGuard, classify_failure


class RecoveryGuardTests(unittest.TestCase):
    def test_missing_gh(self):
        self.assertEqual(classify_failure("gh: no se reconoce como nombre de un cmdlet"), "missing_command")

    def test_workspace_denied(self):
        self.assertEqual(classify_failure("Error: Path escapes the allowed workspace"), "workspace_denied")

    def test_git_diff_usage(self):
        self.assertEqual(classify_failure("error: usage: git diff [options]"), "invalid_command")

    def test_token_budget(self):
        self.assertEqual(classify_failure("The model ran out of tokens"), "token_budget")

    def test_block_repeated_failure(self):
        guard = RecoveryGuard()
        args = {"command": "gh pr view 69"}
        self.assertTrue(guard.check("shell_execute", args).allowed)
        guard.record("shell_execute", args, succeeded=False, error="gh: no se reconoce")
        self.assertTrue(guard.check("shell_execute", args).allowed)
        guard.record("shell_execute", args, succeeded=False, error="gh: no se reconoce")
        self.assertFalse(guard.check("shell_execute", args).allowed)

    def test_new_strategy_allowed(self):
        guard = RecoveryGuard(max_repeats=1)
        guard.record("shell_execute", {"command": "gh pr view 69"}, succeeded=False)
        self.assertTrue(guard.check("shell_execute", {"command": "git status"}).allowed)

    def test_success_clears_failure(self):
        guard = RecoveryGuard(max_repeats=1)
        args = {"command": "git status"}
        guard.record("shell_execute", args, succeeded=False)
        guard.record("shell_execute", args, succeeded=True)
        self.assertTrue(guard.check("shell_execute", args).allowed)

    def test_hash_does_not_retain_secret(self):
        fingerprint = RecoveryGuard.fingerprint("tool", {"token": "PRIVATE_TOKEN"})
        self.assertNotIn("PRIVATE_TOKEN", fingerprint)
        self.assertEqual(len(fingerprint), 64)


if __name__ == "__main__":
    unittest.main()
