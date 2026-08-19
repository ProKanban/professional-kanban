"""Schema and coverage checks for skill-trigger evaluation cases."""

import json
import unittest

from tests.support import REPO_ROOT


class EvaluationCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads((REPO_ROOT / "evals" / "cases.json").read_text(encoding="utf-8"))
        cls.cases = cls.payload["cases"]

    def test_case_schema_and_ids(self):
        ids = []
        for case in self.cases:
            self.assertEqual(
                set(case),
                {"id", "prompt", "should_trigger", "expected_behaviors"},
            )
            self.assertIsInstance(case["should_trigger"], bool)
            self.assertTrue(case["prompt"])
            self.assertTrue(case["expected_behaviors"])
            ids.append(case["id"])
        self.assertEqual(len(ids), len(set(ids)))

    def test_positive_and_negative_coverage(self):
        positive = [case for case in self.cases if case["should_trigger"]]
        negative = [case for case in self.cases if not case["should_trigger"]]
        self.assertGreaterEqual(len(positive), 8)
        self.assertGreaterEqual(len(negative), 8)


if __name__ == "__main__":
    unittest.main()
