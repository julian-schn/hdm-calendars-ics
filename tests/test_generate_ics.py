import sys
import unittest
from datetime import date, datetime, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from crawl import Event
from generate_ics import BERLIN_TZ, event_to_ics


class EventToIcsTests(unittest.TestCase):
    def test_all_day_multiweek_event_has_exclusive_end(self):
        ics_event = event_to_ics(
            Event(
                title="Examination period",
                date_start=date(2026, 7, 1),
                date_end=date(2026, 7, 31),
            )
        )
        self.assertEqual(ics_event.decoded("dtstart"), date(2026, 7, 1))
        self.assertEqual(ics_event.decoded("dtend"), date(2026, 8, 1))

    def test_timed_overnight_event_rolls_to_next_day(self):
        ics_event = event_to_ics(
            Event(
                title="Overnight lab",
                date_start=date(2026, 3, 17),
                time_start=time(23, 0),
                time_end=time(1, 0),
            )
        )
        self.assertEqual(
            ics_event.decoded("dtstart"),
            datetime(2026, 3, 17, 23, 0, tzinfo=BERLIN_TZ),
        )
        self.assertEqual(
            ics_event.decoded("dtend"),
            datetime(2026, 3, 18, 1, 0, tzinfo=BERLIN_TZ),
        )

    def test_timed_multiday_event_keeps_explicit_end_date(self):
        ics_event = event_to_ics(
            Event(
                title="Conference",
                date_start=date(2026, 3, 17),
                date_end=date(2026, 3, 20),
                time_start=time(9, 0),
                time_end=time(17, 0),
            )
        )
        self.assertEqual(
            ics_event.decoded("dtend"),
            datetime(2026, 3, 20, 17, 0, tzinfo=BERLIN_TZ),
        )


if __name__ == "__main__":
    unittest.main()
