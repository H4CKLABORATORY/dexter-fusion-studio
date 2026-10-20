import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / "tools" / "hermes" / "checkpoint.py"
spec = importlib.util.spec_from_file_location("hermes_checkpoint", MODULE)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = h.new("H4CKLABORATORY/repo", "task-1", "Diagnosticar fallo", "feature/test", "Revisar error")
        self.dest = h.file_for(self.root, "task-1")

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_and_restore(self):
        h.save(self.dest, self.data)
        self.assertEqual(h.load(self.dest, "task-1"), self.data)

    def test_no_accidental_overwrite(self):
        h.save(self.dest, self.data)
        with self.assertRaises(FileExistsError):
            h.save(self.dest, self.data, overwrite=False)
        self.assertEqual(h.load(self.dest)["task_id"], "task-1")

    def test_unsafe_ids(self):
        for name in ("../escape", "../../x", "a/b", "", "..", "."):
            with self.subTest(name=name), self.assertRaises(ValueError):
                h.file_for(self.root, name)

    def test_detects_new_commit(self):
        self.data["last_observed_commit"] = "a" * 40
        result = h.resume(self.data, "b" * 40)
        self.assertTrue(result["incremental_review_required"])
        self.assertFalse(result["current_commit"] == result["last_observed_commit"])

    def test_verification_requires_evidence(self):
        with self.assertRaises(ValueError):
            h.advance(self.data, status="completed", next_action="Listo",
                      observed_commit="a" * 40, verified_commit="a" * 40)
        with self.assertRaises(ValueError):
            h.advance(self.data, status="completed", next_action="Listo",
                      observed_commit="a" * 40, verified_commit="b" * 40,
                      test_name="CI", test_result="passed", evidence="URL")

    def test_valid_verified_advance(self):
        item = h.advance(self.data, status="in_progress", next_action="Abre PR",
                         observed_commit="a"*40, verified_commit="a"*40,
                         test_name="unit", test_result="passed", evidence="CI #123",
                         step="Implementado", changed_file="foo.py")
        self.assertEqual(item["last_verified_commit"], "a"*40)
        self.assertEqual(h.resume(item, "a"*40)["verification_pending"], False)

    def test_sha_change_resets_verification(self):
        first = h.advance(self.data, status="in_progress", next_action="Revisar",
                          observed_commit="a"*40, verified_commit="a"*40,
                          test_name="ci", test_result="passed", evidence="run#1")
        second = h.advance(first, status="in_progress", next_action="Revisar cambios",
                           observed_commit="b"*40)
        self.assertIsNone(second["last_verified_commit"])
        self.assertTrue(h.resume(second, "b"*40)["verification_pending"])

    def test_corrupted_fails_closed(self):
        self.data["verification"] = [{"name": "mock", "result": "invented", "evidence": "x"}]
        with self.assertRaises(ValueError):
            h.check(self.data)

    def test_cli_end_to_end(self):
        argv = ["--root", str(self.root)]
        self.assertEqual(h.main(argv+["init", "--project", "H4CKLABORATORY/repo", "--task-id", "abc", "--objective", "Prueba", "--branch", "main", "--next-action", "Empezar"]), 0)
        self.assertEqual(h.main(argv+["advance", "--task-id", "abc", "--status", "blocked", "--next-action", "Esperar", "--blocker", "Sin API"]), 0)
        self.assertEqual(h.main(argv+["validate-all"]), 0)
        self.assertEqual(h.load(h.file_for(self.root,"abc"))["status"], "blocked")

    def test_history_bounded(self):
        item = self.data
        for _ in range(100):
            item = h.advance(item, status="in_progress", next_action="Continuar")
        self.assertEqual(len(item["history"]), h.MAX_HISTORY)


if __name__ == "__main__":
    unittest.main()
