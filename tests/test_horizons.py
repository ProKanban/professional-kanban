"""Tests for calendar and sampling-unit horizon semantics."""

from datetime import date
import unittest

from tests.support import FIXTURES_ROOT, SKILL_ROOT, import_scripts, run_cli

import_scripts()
import flowlib  # noqa: E402
import monte_carlo  # noqa: E402


WEEKLY = FIXTURES_ROOT / "weekly-with-zero-edges.csv"
DAILY = SKILL_ROOT / "assets" / "example-completed-items.csv"


class HorizonUnitTests(unittest.TestCase):
    def test_one_calendar_day_on_saturday_has_no_weekday_periods(self):
        saturday = date(2026, 8, 22)
        self.assertEqual(
            monte_carlo.working_periods_between(
                saturday,
                saturday,
                "day",
                flowlib.parse_workdays("mon-fri"),
            ),
            0,
        )


class HorizonCliTests(unittest.TestCase):
    def test_weekly_history_rejects_days_horizon(self):
        result = run_cli(
            "monte_carlo.py",
            "how-many",
            "--input",
            WEEKLY,
            "--days",
            1,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("use --weeks", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_weekly_history_accepts_explicit_weeks_horizon(self):
        result = run_cli(
            "monte_carlo.py",
            "how-many",
            "--input",
            WEEKLY,
            "--weeks",
            2,
            "--trials",
            10,
            "--seed",
            1,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("next 2 weeks", result.stdout)

    def test_weekly_history_rejects_conflicting_day_unit(self):
        result = run_cli(
            "monte_carlo.py",
            "how-many",
            "--input",
            WEEKLY,
            "--weeks",
            2,
            "--unit",
            "day",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("weekly period column", result.stderr)

    def test_one_day_weekend_horizon_forecasts_zero_without_shifting_to_monday(self):
        result = run_cli(
            "monte_carlo.py",
            "how-many",
            "--input",
            DAILY,
            "--start",
            "2026-08-22",
            "--days",
            1,
            "--trials",
            10,
            "--seed",
            1,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("0 working days", result.stdout)
        self.assertIn("85% chance of completing 0 items or more", result.stdout)


if __name__ == "__main__":
    unittest.main()
