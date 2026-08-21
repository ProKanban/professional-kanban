"""Unit tests for cycle-time and aging calculations."""

from datetime import date
import unittest

from tests.support import FIXTURES_ROOT, import_scripts

import_scripts()
import cycle_time  # noqa: E402


class WipValidationTests(unittest.TestCase):
    def test_future_wip_start_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "after the as-of date"):
            cycle_time.load_wip(
                FIXTURES_ROOT / "future-wip.csv",
                date(2026, 8, 1),
            )


class AgingRiskTests(unittest.TestCase):
    def test_conditional_breach_rate_uses_comparable_completed_items(self):
        values = list(range(1, 21))
        breaches, comparable = cycle_time.conditional_breach_rate(values, 15, 19)
        self.assertEqual((breaches, comparable), (1, 6))


if __name__ == "__main__":
    unittest.main()
