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

    def test_weekly_window_boundaries_preserve_the_observed_cadence(self):
        history = monte_carlo.load_throughput(
            FIXTURES_ROOT / "weekly-with-zero-edges.csv",
            None,
            flowlib.parse_workdays("mon-fri"),
            date(2026, 6, 2),
            None,
            None,
        )
        self.assertEqual(history.series, [5, 0])
        self.assertEqual(history.first, date(2026, 6, 8))
        self.assertEqual(history.last, date(2026, 6, 15))
        self.assertEqual(history.item_count, 5)

    def test_irregular_weekly_period_labels_are_rejected(self):
        rows = [
            {"Week Ending": "2026-06-01", "Throughput": "1"},
            {"Week Ending": "2026-06-09", "Throughput": "2"},
        ]
        with self.assertRaisesRegex(ValueError, "same weekday"):
            monte_carlo._load_period_counts(
                rows,
                "Week Ending",
                "Throughput",
                None,
                None,
                None,
                None,
                flowlib.parse_workdays("mon-fri"),
            )

    def test_positive_non_workday_counts_are_rejected(self):
        rows = [
            {"Date": "2026-08-21", "Throughput": "1"},
            {"Date": "2026-08-22", "Throughput": "5"},
            {"Date": "2026-08-24", "Throughput": "2"},
        ]
        with self.assertRaisesRegex(ValueError, "--workdays"):
            monte_carlo._load_period_counts(
                rows,
                "Date",
                "Throughput",
                None,
                None,
                None,
                None,
                flowlib.parse_workdays("mon-fri"),
            )


if __name__ == "__main__":
    unittest.main()
