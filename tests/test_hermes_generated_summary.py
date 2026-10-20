"""Functional tests for Ollama-produced checkpoint summary after human review."""
import copy
from pathlib import Path
import unittest

from tools.hermes import checkpoint as cp
from tools.hermes import cloud_ai_worker as ai
from tools.hermes.experiments.checkpoint_summary import summarize_checkpoint


class GeneratedSummaryTests(unittest.TestCase):
    def setUp(self):
        self.record = cp.new(
            "H4CKLABORATORY/dexter-fusion-studio", "first-ai-proposal",
            "Summarize checkpoint", "feature/sample", "Check CI",
        )

    def test_reviewed_helper_still_passes_bot_static_policy(self):
        source = Path("tools/hermes/experiments/checkpoint_summary.py").read_text(encoding="utf-8")
        self.assertEqual(ai.validate_code(source), source)

    def test_new_checkpoint_matches_resume_contract(self):
        result = summarize_checkpoint(self.record)
        self.assertFalse(result["verification_pending"])
        self.assertEqual(result["verification_pending"],
                         cp.resume(self.record)["verification_pending"])
        self.assertEqual(result["blockers_count"], 0)
        self.assertEqual(set(result), {
            "task_id", "project", "status", "next_action",
            "blockers_count", "verification_pending",
        })

    def test_verified_commit_matches_observed(self):
        data = cp.advance(self.record, status="in_progress", next_action="Review",
                          observed_commit="a" * 40, verified_commit="a" * 40,
                          test_name="unit", test_result="passed", evidence="CI 123")
        self.assertEqual(summarize_checkpoint(data)["verification_pending"],
                         cp.resume(data)["verification_pending"])
        self.assertFalse(summarize_checkpoint(data)["verification_pending"])

    def test_commit_changed_requires_verification(self):
        verified = cp.advance(self.record, status="in_progress", next_action="Review",
                              observed_commit="a" * 40, verified_commit="a" * 40,
                              test_name="unit", test_result="passed", evidence="CI 123")
        changed = cp.advance(verified, status="in_progress",
                             next_action="Check diff", observed_commit="b" * 40)
        self.assertTrue(summarize_checkpoint(changed)["verification_pending"])
        self.assertEqual(summarize_checkpoint(changed)["verification_pending"],
                         cp.resume(changed)["verification_pending"])

    def test_stale_verified_sha_is_pending(self):
        self.record["last_observed_commit"] = "a" * 40
        self.record["last_verified_commit"] = "b" * 40
        self.assertTrue(summarize_checkpoint(self.record)["verification_pending"])

    def test_sha_case_normalization(self):
        self.record["last_observed_commit"] = "ABCDEF012345"
        self.record["last_verified_commit"] = "abcdef012345"
        self.assertFalse(summarize_checkpoint(self.record)["verification_pending"])

    def test_empty_sha_represents_unset(self):
        self.record["last_observed_commit"] = ""
        self.record["last_verified_commit"] = None
        self.assertFalse(summarize_checkpoint(self.record)["verification_pending"])

    def test_required_fields_rejected_when_absent(self):
        for field in ("task_id", "project", "status", "next_action", "blockers",
                      "last_observed_commit", "last_verified_commit"):
            record = dict(self.record)
            record.pop(field)
            with self.subTest(field=field), self.assertRaises(ValueError):
                summarize_checkpoint(record)

    def test_reject_non_dict_inputs(self):
        for value in (None, [], "checkpoint", 42):
            with self.subTest(value=value), self.assertRaises(ValueError):
                summarize_checkpoint(value)

    def test_reject_invalid_status(self):
        for status in (None, [], 5, "done"):
            with self.subTest(status=status), self.assertRaises(ValueError):
                summarize_checkpoint(dict(self.record, status=status))

    def test_reject_invalid_text_fields(self):
        for field in ("task_id", "project", "next_action"):
            for value in (None, "", "   ", [], 2, "a" * 2001):
                record = dict(self.record)
                record[field] = value
                with self.subTest(field=field, value=repr(value)[:20]), self.assertRaises(ValueError):
                    summarize_checkpoint(record)

    def test_blocker_count_without_disclosing_contents(self):
        self.record["blockers"] = ["secret reason 1", "secret reason 2"]
        result = summarize_checkpoint(self.record)
        self.assertEqual(result["blockers_count"], 2)
        self.assertNotIn("secret reason", str(result))

    def test_reject_malformed_blockers(self):
        for blockers in (None, "not a list", {}, ["valid", 1], [None], ("x",)):
            with self.subTest(blockers=blockers), self.assertRaises(ValueError):
                summarize_checkpoint(dict(self.record, blockers=blockers))

    def test_reject_invalid_commit_values(self):
        for field in ("last_observed_commit", "last_verified_commit"):
            for value in (123, [], "zzzzzzz", "a" * 6, "a" * 65, "abcdefG"):
                record = dict(self.record)
                record[field] = value
                with self.subTest(field=field, value=str(value)[:12]), self.assertRaises(ValueError):
                    summarize_checkpoint(record)

    def test_source_record_not_modified(self):
        self.record["blockers"] = ["a blocker"]
        before = copy.deepcopy(self.record)
        summarize_checkpoint(self.record)
        self.assertEqual(self.record, before)

    def test_extra_secret_fields_never_echoed(self):
        self.record["private_token"] = "not-for-summary"
        self.assertNotIn("not-for-summary", str(summarize_checkpoint(self.record)))

    def test_whitespace_normalization(self):
        self.record["project"] = " project "
        self.record["next_action"] = " continue "
        result = summarize_checkpoint(self.record)
        self.assertEqual(result["project"], "project")
        self.assertEqual(result["next_action"], "continue")


if __name__ == "__main__":
    unittest.main()
