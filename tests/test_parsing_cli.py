"""CLI regressions for date and column parsing."""

import unittest

from tests.support import FIXTURES_ROOT, SKILL_ROOT, run_cli


SAMPLE = SKILL_ROOT / "assets" / "example-completed-items.csv"


class ParsingCliTests(unittest.TestCase):
    def test_country_column_is_ignored_for_completion_rows(self):
        result = run_cli(
            "monte_carlo.py",
            "how-many",
            "--input",
            FIXTURES_ROOT / "completed-with-country.csv",
            "--days",
            5,
            "--trials",
            10,
            "--seed",
            1,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Items completed: 2", result.stdout)

    def test_ambiguous_csv_date_requires_date_order(self):
        result = run_cli(
            "cycle_time.py",
            "sle",
            "--input",
            FIXTURES_ROOT / "ambiguous-dates.csv",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("ambiguous date", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_mdy_csv_date_order_produces_intended_cycle_time(self):
        result = run_cli(
            "cycle_time.py",
            "sle",
            "--input",
            FIXTURES_ROOT / "ambiguous-dates.csv",
            "--date-order",
            "mdy",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("43", result.stdout)

    def test_invalid_window_date_is_not_silently_ignored(self):
        result = run_cli(
            "monte_carlo.py",
            "how-many",
            "--input",
            SAMPLE,
            "--days",
            30,
            "--from",
            "nonsense",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("--from must use YYYY-MM-DD", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_reversed_window_is_rejected(self):
        result = run_cli(
            "monte_carlo.py",
            "how-many",
            "--input",
            SAMPLE,
            "--days",
            30,
            "--from",
            "2026-08-01",
            "--to",
            "2026-07-01",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("--from must be on or before --to", result.stderr)


if __name__ == "__main__":
    unittest.main()
