"""Tests for lossless historical throughput loading."""

from datetime import date
import unittest

from tests.support import FIXTURES_ROOT, import_scripts, run_cli

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


class WeekendCompletionTests(unittest.TestCase):
    """A completion finished on a non-working day is real output, never discarded."""

    FIXTURE = FIXTURES_ROOT / "weekend-completions.csv"

    def test_all_days_samples_every_calendar_day(self):
        history = monte_carlo.load_throughput(
            self.FIXTURE, None, flowlib.parse_workdays("all"), None, None, None
        )
        self.assertEqual(history.series, [2, 1, 0, 1, 0, 2, 1, 1, 0, 2, 0, 0, 1, 2])
        self.assertEqual(history.item_count, 13)

    def test_weekday_mode_folds_weekend_finishes_into_the_next_working_day(self):
        series, first, last = flowlib.daily_throughput(
            [date(2026, 6, 5), date(2026, 6, 6), date(2026, 6, 7), date(2026, 6, 8)],
            flowlib.parse_workdays("mon-fri"),
        )
        self.assertEqual(series, [1, 3])

    def test_weekday_mode_folds_a_trailing_weekend_into_the_last_working_day(self):
        history = monte_carlo.load_throughput(
            self.FIXTURE, None, flowlib.parse_workdays("mon-fri"), None, None, None
        )
        self.assertEqual(history.series, [2, 1, 0, 1, 0, 4, 0, 2, 0, 3])
        self.assertEqual(sum(history.series), history.item_count)

    def test_default_workdays_sample_calendar_days(self):
        result = run_cli(
            "monte_carlo.py", "how-many", "--input", self.FIXTURE,
            "--days", 7, "--trials", 10, "--seed", 1,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Items completed: 13 over 14 days", result.stdout)


if __name__ == "__main__":
    unittest.main()
