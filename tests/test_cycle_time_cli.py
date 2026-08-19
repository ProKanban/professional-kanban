"""CLI regressions for cycle-time and aging output."""

import unittest

from tests.support import FIXTURES_ROOT, run_cli


HISTORY = FIXTURES_ROOT / "custom-risk-cycle-times.csv"
WIP = FIXTURES_ROOT / "custom-risk-wip.csv"


class CycleTimeCliTests(unittest.TestCase):
    def assert_cli_error(self, expected, *args):
        result = run_cli("cycle_time.py", *args)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn(expected, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_non_finite_cycle_time_is_rejected(self):
        self.assert_cli_error(
            "finite positive number",
            "sle", "--input", FIXTURES_ROOT / "non-finite-cycle-times.csv",
        )

    def test_cycle_time_only_input_rejects_date_window(self):
        self.assert_cli_error(
            "cannot apply --from or --to",
            "sle", "--input", HISTORY, "--from", "2026-01-01",
        )

    def test_future_wip_start_is_a_clean_cli_error(self):
        self.assert_cli_error(
            "after the as-of date",
            "aging", "--input", HISTORY,
            "--wip", FIXTURES_ROOT / "future-wip.csv",
            "--as-of", "2026-08-01",
        )

    def test_percentiles_must_be_finite_open_interval_values(self):
        for value in ("", "0,85", "85,100", "nan,85", "abc"):
            with self.subTest(value=value):
                self.assert_cli_error(
                    "--percentiles values must be finite numbers between 0 and 100",
                    "sle", "--input", HISTORY, "--percentiles", value,
                )

    def test_sle_must_be_a_finite_open_interval_value(self):
        for value in ("0", "100", "nan", "inf"):
            with self.subTest(value=value):
                self.assert_cli_error(
                    "--sle must be a finite number between 0 and 100",
                    "sle", "--input", HISTORY, "--sle", value,
                )

    def test_custom_sle_uses_empirical_conditional_risk(self):
        result = run_cli(
            "cycle_time.py", "aging", "--input", HISTORY, "--wip", WIP,
            "--as-of", "2026-08-20", "--sle", 95,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("17% observed breach rate", result.stdout)
        self.assertNotIn("roughly a 50% chance", result.stdout)

    def test_custom_display_percentiles_keep_internal_aging_thresholds(self):
        result = run_cli(
            "cycle_time.py", "aging", "--input", HISTORY, "--wip", WIP,
            "--as-of", "2026-08-20", "--percentiles", "60,80", "--sle", 85,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("WATCH-11", result.stdout)
        self.assertIn("past the 50th", result.stdout)

    def test_sle_rejects_aging_only_flags(self):
        self.assert_cli_error(
            "--wip and --as-of are only valid with aging",
            "sle", "--input", HISTORY, "--wip", WIP, "--as-of", "2026-08-20",
        )

    def test_missing_input_file_is_a_clean_error(self):
        self.assert_cli_error(
            "No such file or directory",
            "sle", "--input", "does-not-exist.csv",
        )


if __name__ == "__main__":
    unittest.main()
