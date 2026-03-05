import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from crawl import parse_date_text


class ParseDateTextTests(unittest.TestCase):
    def test_german_cross_month_range(self):
        start, end = parse_date_text("17. März - 03. Juli 2026", "de")
        self.assertEqual(start, date(2026, 3, 17))
        self.assertEqual(end, date(2026, 7, 3))

    def test_german_multiweek_range(self):
        start, end = parse_date_text("01. Juli 2026 - 31. Juli 2026", "de")
        self.assertEqual(start, date(2026, 7, 1))
        self.assertEqual(end, date(2026, 7, 31))

    def test_english_full_range(self):
        start, end = parse_date_text("March 17, 2026 - March 20, 2026", "en")
        self.assertEqual(start, date(2026, 3, 17))
        self.assertEqual(end, date(2026, 3, 20))

    def test_english_short_range(self):
        start, end = parse_date_text("March 17 - 20, 2026", "en")
        self.assertEqual(start, date(2026, 3, 17))
        self.assertEqual(end, date(2026, 3, 20))

    def test_english_single_date(self):
        start, end = parse_date_text("March 17, 2026", "en")
        self.assertEqual(start, date(2026, 3, 17))
        self.assertIsNone(end)


if __name__ == "__main__":
    unittest.main()
