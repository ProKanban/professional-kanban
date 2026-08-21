"""Unit tests for shared parsing and statistical helpers."""

from datetime import date
import unittest

from tests.support import import_scripts

import_scripts()
import flowlib  # noqa: E402


class DateParsingTests(unittest.TestCase):
    def test_ambiguous_numeric_date_requires_order(self):
        with self.assertRaisesRegex(ValueError, "ambiguous date"):
            flowlib.parse_date("05/01/2026")

    def test_explicit_mdy_resolves_ambiguous_date(self):
        self.assertEqual(
            flowlib.parse_date("05/01/2026", date_order="mdy"),
            date(2026, 5, 1),
        )

    def test_explicit_dmy_resolves_ambiguous_date(self):
        self.assertEqual(
            flowlib.parse_date("05/01/2026", date_order="dmy"),
            date(2026, 1, 5),
        )

    def test_unambiguous_numeric_dates_do_not_need_an_order(self):
        self.assertEqual(flowlib.parse_date("13/04/2026"), date(2026, 4, 13))
        self.assertEqual(flowlib.parse_date("04/13/2026"), date(2026, 4, 13))

    def test_strict_iso_rejects_other_formats(self):
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            flowlib.parse_date("13/04/2026", strict_iso=True)

    def test_strict_iso_rejects_timestamp_suffixes(self):
        for value in ("2026-08-19Tgarbage", "2026-08-19 25:99:99"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
                    flowlib.parse_date(value, strict_iso=True)


class ColumnDetectionTests(unittest.TestCase):
    def test_country_does_not_match_count(self):
        headers = {"country": "Country", "completeddate": "Completed Date"}
        self.assertIsNone(flowlib.find_column(headers, flowlib.COUNT_NAMES))

    def test_account_does_not_match_count(self):
        headers = {"account": "Account", "completeddate": "Completed Date"}
        self.assertIsNone(flowlib.find_column(headers, flowlib.COUNT_NAMES))

    def test_token_fallback_matches_decorated_header(self):
        headers = {"storyfinishedon": "story_finished_on"}
        self.assertEqual(
            flowlib.find_column(headers, flowlib.FINISHED_NAMES),
            "story_finished_on",
        )

    def test_decorated_delivered_alias_is_a_count_column(self):
        headers = {"weekending": "Week Ending", "workdelivered": "Work Delivered"}
        self.assertEqual(
            flowlib.find_column(headers, flowlib.COUNT_NAMES),
            "Work Delivered",
        )


if __name__ == "__main__":
    unittest.main()
