# ICS Generation Specification

## Purpose
Convert a list of structured event dictionaries into a valid iCalendar (`.ics`) file.

## Input
- `events` (list): Event dictionaries as defined in `crawl.spec.md`
- `calendar_name` (string): Display name for the calendar (X-WR-CALNAME)

## Output
A UTF-8 encoded string containing a valid iCalendar document (RFC 5545).

## Calendar Properties

```
PRODID:-//hdm-calendars-ics//HdM Calendar Crawler//EN
VERSION:2.0
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:{calendar_name}
X-WR-TIMEZONE:Europe/Berlin
```

## Event Mapping

| Event Field    | ICS Property    | Notes                                              |
|----------------|-----------------|---------------------------------------------------|
| `title`        | `SUMMARY`       | Required                                           |
| `date_start`   | `DTSTART`       | `VALUE=DATE` if all-day, `TZID=Europe/Berlin` if timed |
| `date_end`     | `DTEND`         | Same format as DTSTART. If missing, DTSTART + 1 day for all-day |
| `time_start`   | (merged into DTSTART) | Combined with date_start                    |
| `time_end`     | (merged into DTEND)   | Combined with date_end or date_start        |
| `location`     | `LOCATION`      | Optional                                           |
| `description`  | `DESCRIPTION`   | Optional                                           |
| `url`          | `URL`           | Optional, link to detail page                      |

## Rules

1. **All-day events:** If no `time_start` is provided, create as all-day event (`VALUE=DATE`)
   - For multi-day and multi-week all-day events (e.g. examination periods), `DTEND` is exclusive and must be `date_end + 1 day`
2. **Timed events:** If `time_start` is provided, use `TZID=Europe/Berlin`
   - If `time_end` is earlier than or equal to `time_start` on the same date, treat it as crossing midnight (end on next day)
3. **UID generation:** `{date_start}-{slugified_title}@hdm-calendars-ics` — deterministic so repeated runs don't create duplicates
4. **DTSTAMP:** Set to current UTC time at generation
5. **Timezone:** Always Europe/Berlin (VTIMEZONE component included)
6. **Encoding:** UTF-8, CRLF line endings per RFC 5545
