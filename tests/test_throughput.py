"""Tests for lossless historical throughput loading."""

from datetime import date
import unittest

from tests.support import FIXTURES_ROOT, import_scripts

import_scripts()
import flowlib  # noqa: E402
import monte_carlo  # noqa: E402


class ThroughputLoadingTests(unittest.TestCase):
    def test_period_counts_preserve_zero_edges(self):
        history = monte_carlo.load_throughput(
            FIXTURES_ROOT / "weekly-with-zero-edges.csv",
            None,
            flowlib.parse_workdays("mon-fri"),
            None,
            None,
            None,
        )
        self.assertEqual(history.series, [0, 5, 0])
        self.assertEqual(history.first, date(2026, 6, 1))
        self.assertEqual(history.last, date(2026, 6, 15))
        self.assertEqual(history.item_count, 5)
        self.assertEqual(history.unit, "week")

    def test_period_counts_do_not_expand_into_one_entry_per_item(self):
        history = monte_carlo.load_throughput(
            FIXTURES_ROOT / "weekly-with-zero-edges.csv",
            None,
            flowlib.parse_workdays("mon-fri"),
            None,
            None,
            None,
        )
        self.assertEqual(len(history.series), 3)


if __name__ == "__main__":
    unittest.main()
