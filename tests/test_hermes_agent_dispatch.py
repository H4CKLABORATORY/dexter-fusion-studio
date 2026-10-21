"""Pruebas del planificador multiagente sin dependencias externas."""
import unittest
from tools.hermes.agent_dispatch import plan


def task(ident, deps=(), role="backend"):
    return {"id": ident, "role": role, "prompt": "Analiza y propone", "depends_on": list(deps)}


class AgentPlanTests(unittest.TestCase):
    def test_parallel_and_dependency(self):
        batches = plan({"tasks": [task("qa", ["front", "back"], "qa"), task("front", role="frontend"), task("back")]})
        self.assertEqual([[x["id"] for x in batch] for batch in batches], [["front", "back"], ["qa"]])

    def test_cycle_rejected(self):
        with self.assertRaisesRegex(ValueError, "cíclicas"):
            plan({"tasks": [task("a", ["b"]), task("b", ["a"])]})

    def test_unknown_dependency_rejected(self):
        with self.assertRaisesRegex(ValueError, "desconocida"):
            plan({"tasks": [task("a", ["missing"])]})

    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            plan({"tasks": [task("a"), task("a")]})

    def test_bad_role_rejected(self):
        with self.assertRaises(ValueError):
            plan({"tasks": [task("a", role="superuser")]})

    def test_unhashable_role_rejected_as_validation_error(self):
        for role in ([], {}, None, 3):
            with self.subTest(role=role), self.assertRaises(ValueError):
                plan({"tasks": [task("a", role=role)]})

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            plan({"tasks": []})


if __name__ == "__main__":
    unittest.main()
