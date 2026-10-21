"""Tests for local shared context: no network, no LU account, no user files."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "tools" / "lu-memory" / "sync_context.py"
spec = importlib.util.spec_from_file_location("dexter_lu_sync", MODULE)
lu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lu)


class LocalMemoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.parent = self.base / "repos"
        self.parent.mkdir()
        self.a = self.parent / "dexter-fusion-studio"
        self.b = self.parent / "1UP-ANIME"
        for folder in (self.a, self.b):
            (folder / ".git" / "info").mkdir(parents=True)
        self.home = self.base / "private-memory"

    def test_generates_rules_and_state_and_private_ignore(self):
        roots = lu.discover([], [str(self.parent)])
        self.assertEqual(len(roots), 2)
        lu.sync(roots, self.home)
        self.assertTrue((self.a / ".lurules").exists())
        self.assertTrue((self.b / ".dexter-local" / "LAST_SESSION.md").exists())
        self.assertIn(".dexter-local/", (self.a / ".git" / "info" / "exclude").read_text())
        self.assertTrue((self.home / "MASTER_CONTEXT.md").exists())

    def test_existing_rules_and_session_are_not_overwritten(self):
        (self.a / ".lurules").write_text("REGRA ACTUAL\n", encoding="utf-8")
        lu.sync([self.a], self.home)
        (self.a / ".dexter-local" / "LAST_SESSION.md").write_text("commit probado: abc\n", encoding="utf-8")
        lu.sync([self.a], self.home)
        self.assertEqual((self.a / ".lurules").read_text(), "REGRA ACTUAL\n")
        self.assertEqual((self.a / ".dexter-local" / "LAST_SESSION.md").read_text(), "commit probado: abc\n")
        self.assertEqual((self.a / ".git" / "info" / "exclude").read_text().count(".dexter-local/"), 1)

    def test_new_checkpoint_is_shared_after_explicit_resync(self):
        roots = lu.discover([], [str(self.parent)])
        lu.sync(roots, self.home)
        (self.a / ".dexter-local" / "LAST_SESSION.md").write_text(
            "Fusion Studio: prueba local aprobada\n", encoding="utf-8"
        )
        lu.sync(roots, self.home)
        shared = (self.b / ".dexter-local" / "SHARED_CONTEXT.md").read_text(encoding="utf-8")
        self.assertIn("Fusion Studio: prueba local aprobada", shared)

    def test_only_one_directory_deep_scanned(self):
        third = self.parent / "deep" / "nested-project"
        (third / ".git").mkdir(parents=True)
        roots = lu.discover([], [str(self.parent)])
        self.assertEqual(len(roots), 2)


if __name__ == "__main__":
    unittest.main()
