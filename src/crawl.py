"""
Crawler for HdM Stuttgart calendar pages.

Fetches calendar listing pages, extracts event data from the HTML,
and optionally follows detail links for additional information.
"""

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import date, time as dt_time
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# German month names → month numbers
GERMAN_MONTHS = {
    "januar": 1, "februar": 2, "märz": 3, "april": 4,
    "mai": 5, "juni": 6, "juli": 7, "august": 8,
    "september": 9, "oktober": 10, "november": 11, "dezember": 12,
}

# English month names → month numbers
ENGLISH_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]


@dataclass
class Event:
    """A parsed calendar event."""
    title: str
    date_start: date
    date_end: Optional[date] = None
    time_start: Optional[dt_time] = None
    time_end: Optional[dt_time] = None
    location: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None


def fetch_page(url: str) -> str:
    """Fetch a URL with retry logic. Returns HTML string."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers={
                "User-Agent": "hdm-calendars-ics/1.0 (GitHub Actions calendar crawler)"
            })
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF[attempt]
                logger.warning(f"Retry {attempt + 1}/{MAX_RETRIES} for {url} after {wait}s: {e}")
                time.sleep(wait)
            else:
                raise


def parse_month(month_str: str, language: str) -> int:
    """Parse a month name to its number."""
    month_lower = month_str.strip().lower().rstrip(".")
    months = GERMAN_MONTHS if language == "de" else ENGLISH_MONTHS
    if month_lower in months:
        return months[month_lower]
    # Try abbreviated form (first 3 chars)
    for name, num in months.items():
        if name.startswith(month_lower) or month_lower.startswith(name[:3]):
            return num
    raise ValueError(f"Unknown month: {month_str!r} (language={language})")


def parse_date_text(text: str, language: str) -> tuple[date, Optional[date]]:
    """
    Parse German/English date strings into (start_date, end_date).

    Handles formats:
    - "17. März 2026"
    - "17.03.2026"
    - "05. März 2026 - 16. März 2026"
    - "17. - 20. März 2026"
    - "March 17, 2026"
    """
    text = re.sub(r"\s+", " ", text.strip()).replace("–", "-").replace("—", "-")
    month_pattern = r"([A-Za-zÄÖÜäöüß]+)\.?"

    # Try "DD.MM.YYYY" numeric format
    numeric_range = re.fullmatch(
        r"(\d{1,2})\.(\d{1,2})\.(\d{4})\s*-\s*(\d{1,2})\.(\d{1,2})\.(\d{4})",
        text
    )
    if numeric_range:
        d1, m1, y1 = int(numeric_range.group(1)), int(numeric_range.group(2)), int(numeric_range.group(3))
        d2, m2, y2 = int(numeric_range.group(4)), int(numeric_range.group(5)), int(numeric_range.group(6))
        return date(y1, m1, d1), date(y2, m2, d2)

    numeric_single = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
    if numeric_single:
        d, m, y = int(numeric_single.group(1)), int(numeric_single.group(2)), int(numeric_single.group(3))
        return date(y, m, d), None

    # Try "DD. Month YYYY - DD. Month YYYY" range with full months
    range_full = re.fullmatch(
        rf"(\d{{1,2}})\.\s*{month_pattern}\s+(\d{{4}})\s*-\s*(\d{{1,2}})\.\s*{month_pattern}\s+(\d{{4}})",
        text
    )
    if range_full:
        d1 = int(range_full.group(1))
        m1 = parse_month(range_full.group(2), language)
        y1 = int(range_full.group(3))
        d2 = int(range_full.group(4))
        m2 = parse_month(range_full.group(5), language)
        y2 = int(range_full.group(6))
        return date(y1, m1, d1), date(y2, m2, d2)

    # Try "DD. Month - DD. Month YYYY" range with one year (German)
    range_cross_month = re.fullmatch(
        rf"(\d{{1,2}})\.\s*{month_pattern}\s*-\s*(\d{{1,2}})\.\s*{month_pattern}\s+(\d{{4}})",
        text
    )
    if range_cross_month:
        d1 = int(range_cross_month.group(1))
        m1 = parse_month(range_cross_month.group(2), language)
        d2 = int(range_cross_month.group(3))
        m2 = parse_month(range_cross_month.group(4), language)
        y = int(range_cross_month.group(5))
        start = date(y, m1, d1)
        end = date(y, m2, d2)
        if end < start:
            end = date(y + 1, m2, d2)
        return start, end

    # Try "DD. - DD. Month YYYY" short range (same month)
    range_short = re.fullmatch(
        rf"(\d{{1,2}})\.\s*-\s*(\d{{1,2}})\.\s*{month_pattern}\s+(\d{{4}})",
        text
    )
    if range_short:
        d1 = int(range_short.group(1))
        d2 = int(range_short.group(2))
        m = parse_month(range_short.group(3), language)
        y = int(range_short.group(4))
        return date(y, m, d1), date(y, m, d2)

    # Try "DD. Month YYYY" single date (German)
    single_de = re.fullmatch(rf"(\d{{1,2}})\.\s*{month_pattern}\s+(\d{{4}})", text)
    if single_de:
        d = int(single_de.group(1))
        m = parse_month(single_de.group(2), language)
        y = int(single_de.group(3))
        return date(y, m, d), None

    # Try "DD Month YYYY - DD Month YYYY" range (no dot, EN academic calendar)
    range_dd_month = re.fullmatch(
        rf"(\d{{1,2}})\s+{month_pattern}\s+(\d{{4}})\s*-\s*(\d{{1,2}})\s+{month_pattern}\s+(\d{{4}})",
        text
    )
    if range_dd_month:
        d1 = int(range_dd_month.group(1))
        m1 = parse_month(range_dd_month.group(2), language)
        y1 = int(range_dd_month.group(3))
        d2 = int(range_dd_month.group(4))
        m2 = parse_month(range_dd_month.group(5), language)
        y2 = int(range_dd_month.group(6))
        return date(y1, m1, d1), date(y2, m2, d2)

    # Try "DD Month YYYY" single date (no dot, EN academic calendar)
    single_dd_month = re.fullmatch(rf"(\d{{1,2}})\s+{month_pattern}\s+(\d{{4}})", text)
    if single_dd_month:
        d = int(single_dd_month.group(1))
        m = parse_month(single_dd_month.group(2), language)
        y = int(single_dd_month.group(3))
        return date(y, m, d), None

    # Try "Month DD, YYYY - Month DD, YYYY" range (English)
    range_en_full = re.fullmatch(
        rf"{month_pattern}\s+(\d{{1,2}}),?\s+(\d{{4}})\s*-\s*{month_pattern}\s+(\d{{1,2}}),?\s+(\d{{4}})",
        text
    )
    if range_en_full:
        m1 = parse_month(range_en_full.group(1), language)
        d1 = int(range_en_full.group(2))
        y1 = int(range_en_full.group(3))
        m2 = parse_month(range_en_full.group(4), language)
        d2 = int(range_en_full.group(5))
        y2 = int(range_en_full.group(6))
        return date(y1, m1, d1), date(y2, m2, d2)

    # Try "Month DD - DD, YYYY" short range (same month, English)
    range_en_short = re.fullmatch(
        rf"{month_pattern}\s+(\d{{1,2}})\s*-\s*(\d{{1,2}}),?\s+(\d{{4}})",
        text
    )
    if range_en_short:
        m = parse_month(range_en_short.group(1), language)
        d1 = int(range_en_short.group(2))
        d2 = int(range_en_short.group(3))
        y = int(range_en_short.group(4))
        return date(y, m, d1), date(y, m, d2)

    # Try "Month DD, YYYY" single date (English)
    single_en = re.fullmatch(rf"{month_pattern}\s+(\d{{1,2}}),?\s+(\d{{4}})", text)
    if single_en:
        m = parse_month(single_en.group(1), language)
        d = int(single_en.group(2))
        y = int(single_en.group(3))
        return date(y, m, d), None

    raise ValueError(f"Cannot parse date: {text!r}")


def parse_time_text(text: str) -> tuple[Optional[dt_time], Optional[dt_time]]:
    """
    Parse a time string like "14:00 - 17:00 Uhr" or "14:00 Uhr".
    Returns (start_time, end_time).
    """
    text = text.strip().replace("Uhr", "").strip()

    # Range: "14:00 - 17:00"
    range_match = re.match(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", text)
    if range_match:
        t1 = dt_time(int(range_match.group(1)), int(range_match.group(2)))
        t2 = dt_time(int(range_match.group(3)), int(range_match.group(4)))
        return t1, t2

    # Single: "14:00"
    single_match = re.match(r"(\d{1,2}):(\d{2})", text)
    if single_match:
        t = dt_time(int(single_match.group(1)), int(single_match.group(2)))
        return t, None

    return None, None


def parse_listing_entry(entry, language: str, base_url: str) -> Optional[Event]:
    """Parse a single .calendar-preview-list-entry element into an Event."""
    try:
        # Extract title
        title_el = entry.select_one("h2") or entry.select_one("h3")
        if not title_el:
            logger.warning("No title found in entry, skipping")
            return None
        title = title_el.get_text(strip=True)

        # Extract date from the info fields (more reliable than the date box)
        date_start = None
        date_end = None
        time_start = None
        time_end = None
        location = None

        infos = entry.select(".calendar-preview-list-entry-info")
        for info in infos:
            icon = info.select_one("i")
            text = info.get_text(strip=True)
            if not icon or not text:
                continue

            icon_classes = icon.get("class", [])
            if "bi-calendar" in icon_classes:
                try:
                    date_start, date_end = parse_date_text(text, language)
                except ValueError as e:
                    logger.warning(f"Failed to parse date '{text}' for '{title}': {e}")
            elif "bi-clock" in icon_classes:
                time_start, time_end = parse_time_text(text)
            elif "bi-geo-alt" in icon_classes:
                location = text

        # Fallback: akademisch calendar uses a different structure
        # with .calendar-show-date/.calendar-show-time/.calendar-show-location
        # inside the infos container (spans with bi-calendar-week icons)
        if date_start is None:
            infos_container = entry.select_one(".calendar-preview-list-entry-infos")
            if infos_container:
                # Date
                show_date = infos_container.select_one(".calendar-show-date")
                if show_date:
                    # The date text is in the second span (first is the icon)
                    spans = show_date.select("span")
                    for span in spans:
                        span_classes = span.get("class", [])
                        # Skip the icon span
                        if any("bi" in c for c in span_classes):
                            continue
                        text = span.get_text(strip=True)
                        if text:
                            try:
                                date_start, date_end = parse_date_text(text, language)
                            except ValueError as e:
                                logger.warning(f"Failed to parse show-date '{text}' for '{title}': {e}")
                            break

                # Time
                show_time = infos_container.select_one(".calendar-show-time")
                if show_time:
                    spans = show_time.select("span")
                    for span in spans:
                        span_classes = span.get("class", [])
                        if any("bi" in c for c in span_classes):
                            continue
                        text = span.get_text(strip=True)
                        if text:
                            time_start, time_end = parse_time_text(text)
                            break

                # Location
                show_loc = infos_container.select_one(".calendar-show-location")
                if show_loc:
                    spans = show_loc.select("span")
                    for span in spans:
                        span_classes = span.get("class", [])
                        if any("bi" in c for c in span_classes):
                            continue
                        text = span.get_text(strip=True)
                        if text:
                            location = text
                            break

        # Fallback: parse date from the date box if no date found in info fields
        if date_start is None:
            date_box = entry.select_one(".calendar-preview-list-entry-date")
            if date_box:
                spans = date_box.select("span")
                if len(spans) >= 2:
                    day_str = spans[0].get_text(strip=True)
                    month_str = spans[1].get_text(strip=True)
                    try:
                        day = int(day_str)
                        month = parse_month(month_str, language)
                        # Infer year: use current year, or next year if month is in the past
                        from datetime import datetime
                        now = datetime.now()
                        year = now.year
                        candidate = date(year, month, day)
                        if candidate < now.date() - __import__("datetime").timedelta(days=60):
                            year += 1
                        date_start = date(year, month, day)
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Failed to parse date box for '{title}': {e}")

        if date_start is None:
            logger.warning(f"No date found for '{title}', skipping")
            return None

        # Extract detail link
        link = entry.select_one("a.stretched-link")
        detail_url = None
        if link and link.get("href"):
            detail_url = urljoin(base_url, link["href"])

        return Event(
            title=title,
            date_start=date_start,
            date_end=date_end,
            time_start=time_start,
            time_end=time_end,
            location=location,
            url=detail_url,
        )

    except Exception as e:
        logger.warning(f"Failed to parse entry: {e}", exc_info=True)
        return None


def enrich_from_detail_page(event: Event, language: str) -> Event:
    """Follow an event's detail URL to extract additional info."""
    if not event.url:
        return event

    try:
        html = fetch_page(event.url)
        soup = BeautifulSoup(html, "lxml")

        infos = soup.select_one(".calendar-show-infos")
        if not infos:
            return event

        # Date
        date_el = infos.select_one(".calendar-show-date span")
        if date_el:
            try:
                d_start, d_end = parse_date_text(date_el.get_text(strip=True), language)
                event.date_start = d_start
                if d_end:
                    event.date_end = d_end
            except ValueError:
                pass

        # Time
        time_el = infos.select_one(".calendar-show-time span")
        if time_el:
            t_start, t_end = parse_time_text(time_el.get_text(strip=True))
            if t_start:
                event.time_start = t_start
            if t_end:
                event.time_end = t_end

        # Location
        loc_el = infos.select_one(".calendar-show-location span")
        if loc_el:
            event.location = loc_el.get_text(strip=True)

        # Description from main content
        content = soup.select_one(".calendar-show-content")
        if content:
            event.description = content.get_text(strip=True)[:2000]

    except Exception as e:
        logger.warning(f"Failed to enrich event '{event.title}' from {event.url}: {e}")

    return event


def crawl_source(source: dict) -> list[Event]:
    """
    Crawl a calendar source and return a list of Events.

    Args:
        source: A source config dict with keys: url, language, follow_detail_links, name
    """
    source_name = source["name"]
    url = source["url"]
    language = source.get("language", "de")
    follow_details = source.get("follow_detail_links", False)

    logger.info(f"[{source_name}] Crawling {url}")

    try:
        html = fetch_page(url)
    except requests.RequestException as e:
        logger.error(f"[{source_name}] Failed to fetch {url}: {e}")
        return []

    soup = BeautifulSoup(html, "lxml")
    entries = soup.select(".calendar-preview-list-entry")
    logger.info(f"[{source_name}] Found {len(entries)} event entries")

    events = []
    for entry in entries:
        event = parse_listing_entry(entry, language, url)
        if event is None:
            continue

        if follow_details and event.url:
            logger.info(f"[{source_name}] Following detail link for '{event.title}'")
            event = enrich_from_detail_page(event, language)
            # Be polite to the server
            time.sleep(0.5)

        events.append(event)

    logger.info(f"[{source_name}] Extracted {len(events)} events")
    return events
