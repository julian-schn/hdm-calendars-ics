"""
ICS calendar generation from structured event data.

Converts a list of Event objects into a valid iCalendar (.ics) file
following RFC 5545.
"""

import re
from datetime import datetime, timedelta

from icalendar import Calendar, Event as IcsEvent, vText

from crawl import Event

# Timezone: Europe/Berlin
TIMEZONE_ID = "Europe/Berlin"

try:
    import zoneinfo
    BERLIN_TZ = zoneinfo.ZoneInfo(TIMEZONE_ID)
except ImportError:
    from dateutil import tz
    BERLIN_TZ = tz.gettz(TIMEZONE_ID)


def slugify(text: str) -> str:
    """Create a URL-safe slug from text for deterministic UIDs."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")[:80]


def make_uid(event: Event) -> str:
    """Generate a deterministic UID for an event."""
    date_str = event.date_start.isoformat()
    slug = slugify(event.title)
    return f"{date_str}-{slug}@hdm-calendars-ics"


def event_to_ics(event: Event) -> IcsEvent:
    """Convert an Event dataclass to an icalendar Event component."""
    ics_event = IcsEvent()

    ics_event.add("uid", make_uid(event))
    ics_event.add("summary", event.title)
    ics_event.add("dtstamp", datetime.utcnow())

    # Determine if this is an all-day or timed event
    if event.time_start:
        # Timed event
        dt_start = datetime(
            event.date_start.year, event.date_start.month, event.date_start.day,
            event.time_start.hour, event.time_start.minute,
            tzinfo=BERLIN_TZ,
        )
        ics_event.add("dtstart", dt_start)

        if event.time_end:
            end_date = event.date_end if event.date_end else event.date_start
            dt_end = datetime(
                end_date.year, end_date.month, end_date.day,
                event.time_end.hour, event.time_end.minute,
                tzinfo=BERLIN_TZ,
            )
            ics_event.add("dtend", dt_end)
        else:
            # Default: 1 hour duration
            ics_event.add("dtend", dt_start + timedelta(hours=1))
    else:
        # All-day event
        ics_event.add("dtstart", event.date_start)
        if event.date_end:
            # iCal DTEND for all-day events is exclusive, so add 1 day
            ics_event.add("dtend", event.date_end + timedelta(days=1))
        else:
            ics_event.add("dtend", event.date_start + timedelta(days=1))

    # Optional fields
    if event.location:
        ics_event.add("location", event.location)

    if event.description:
        ics_event.add("description", event.description)

    if event.url:
        ics_event.add("url", event.url)

    return ics_event


def generate_calendar(events: list[Event], calendar_name: str) -> bytes:
    """
    Generate a complete iCalendar document from a list of events.

    Returns the ICS content as bytes (UTF-8 encoded).
    """
    cal = Calendar()

    # Calendar metadata
    cal.add("prodid", "-//hdm-calendars-ics//HdM Calendar Crawler//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", calendar_name)
    cal.add("x-wr-timezone", TIMEZONE_ID)

    # Add events
    for event in events:
        ics_event = event_to_ics(event)
        cal.add_component(ics_event)

    return cal.to_ical()
