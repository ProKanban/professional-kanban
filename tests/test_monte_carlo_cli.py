"""CLI validation and safety regressions for Monte Carlo forecasting."""

import unittest

from tests.support import SKILL_ROOT, run_cli


SAMPLE = SKILL_ROOT / "assets" / "example-completed-items.csv"


class MonteCarloValidationTests(unittest.TestCase):
    def assert_cli_error(self, expected, *args):
        result = run_cli("monte_carlo.py", *args)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn(expected, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_split_must_be_positive(self):
        for value in ("0", "-1", "nan", "inf"):
            with self.subTest(value=value):
                self.assert_cli_error(
                    "--split must be a finite number greater than zero",
                    "when", "--input", SAMPLE, "--items", 10, "--split", value,
                )

    def test_trials_must_be_positive(self):
        self.assert_cli_error(
            "--trials must be a positive integer",
            "how-many", "--input", SAMPLE, "--days", 30, "--trials", 0,
        )

    def test_items_must_be_positive(self):
        self.assert_cli_error(
            "--items must be a positive integer",
            "when", "--input", SAMPLE, "--items", 0,
        )

    def test_positive_fractional_split_never_erases_remaining_work(self):
        result = run_cli(
            "monte_carlo.py", "when", "--input", SAMPLE, "--items", 1,
            "--split", "0.1", "--trials", 10, "--seed", 7,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("simulating 1 item", result.stdout)

    def test_days_must_be_positive(self):
        self.assert_cli_error(
            "--days must be a positive integer",
            "how-many", "--input", SAMPLE, "--days", 0,
        )

    def test_confidences_must_be_inside_open_interval(self):
        for value in ("-1,85", "85,100", "nan,85", ""):
            with self.subTest(value=value):
                self.assert_cli_error(
                    "--confidence values must be finite numbers between 0 and 100",
                    "how-many", "--input", SAMPLE, "--days", 30,
                    "--confidence", value,
                )

    def test_invalid_workdays_do_not_raise_traceback(self):
        self.assert_cli_error(
            "Could not read workdays",
            "how-many", "--input", SAMPLE, "--days", 30,
            "--workdays", "bananas",
        )

    def test_multiple_horizons_are_rejected(self):
        self.assert_cli_error(
            "choose exactly one of --days, --weeks, or --by",
            "how-many", "--input", SAMPLE, "--days", 30, "--by", "2026-09-30",
        )

    def test_impossible_safety_cap_does_not_claim_completion(self):
        self.assert_cli_error(
            "cannot complete within the simulation safety limit",
            "when", "--input", SAMPLE, "--items", 1, "--split", "1000000000",
            "--trials", 2, "--seed", 7,
        )


if __name__ == "__main__":
    unittest.main()
