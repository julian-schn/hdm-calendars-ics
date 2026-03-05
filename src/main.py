#!/usr/bin/env python3
"""
HdM Calendars → ICS Pipeline

Reads source configurations, crawls each calendar page,
generates ICS files, and writes them to the output directory.
"""

import json
import logging
import sys
from pathlib import Path

from crawl import crawl_source
from generate_ics import generate_calendar

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT_DIR / "config" / "sources.json"
OUTPUT_DIR = ROOT_DIR / "dist"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_sources() -> list[dict]:
    """Load and validate source configurations."""
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        sources = json.load(f)

    required_keys = {"name", "url", "output", "calendar_name", "language"}
    for i, source in enumerate(sources):
        missing = required_keys - source.keys()
        if missing:
            raise ValueError(f"Source #{i} ({source.get('name', '?')}) missing keys: {missing}")

    return sources


def generate_landing_page(sources: list[dict]) -> str:
    """Generate a simple HTML landing page with calendar subscribe links."""
    rows = ""
    for source in sources:
        lang = "🇩🇪 DE" if source["language"] == "de" else "🇬🇧 EN"
        rows += f"""
        <tr>
            <td>{source['calendar_name']}</td>
            <td>{lang}</td>
            <td><a href="{source['output']}">{source['output']}</a></td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>HdM Calendars – ICS Subscribe</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 700px; margin: 2rem auto; padding: 0 1rem;
            color: #1a1a1a; line-height: 1.6;
        }}
        h1 {{ margin-bottom: 0.5rem; }}
        p {{ margin-bottom: 1.5rem; color: #555; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ text-align: left; padding: 0.75rem; border-bottom: 1px solid #e0e0e0; }}
        th {{ background: #f5f5f5; font-weight: 600; }}
        a {{ color: #e2001a; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .hint {{
            margin-top: 2rem; padding: 1rem; background: #f0f7ff;
            border-radius: 8px; font-size: 0.9rem; color: #333;
        }}
        footer {{ margin-top: 2rem; font-size: 0.8rem; color: #999; }}
    </style>
</head>
<body>
    <h1>📅 HdM Stuttgart Calendars</h1>
    <p>Subscribable webcalendars generated from <a href="https://www.hdm-stuttgart.de">hdm-stuttgart.de</a>.</p>
    <table>
        <thead>
            <tr><th>Calendar</th><th>Language</th><th>ICS File</th></tr>
        </thead>
        <tbody>{rows}
        </tbody>
    </table>
    <div class="hint">
        <strong>How to subscribe:</strong> Copy the ICS link, then in your calendar app
        (Google Calendar, Apple Calendar, Outlook), choose "Add calendar → From URL"
        and paste the full URL.
    </div>
    <footer>Auto-updated daily via GitHub Actions. Source on
        <a href="https://github.com/">GitHub</a>.
    </footer>
</body>
</html>
"""


def main() -> int:
    """Run the full pipeline."""
    logger.info("Loading source configuration")
    sources = load_sources()
    logger.info(f"Loaded {len(sources)} sources")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    success_count = 0
    for source in sources:
        name = source["name"]
        try:
            # Crawl
            events = crawl_source(source)
            if not events:
                logger.warning(f"[{name}] No events found — generating empty calendar")

            # Generate ICS
            ics_data = generate_calendar(events, source["calendar_name"])

            # Write output
            output_path = OUTPUT_DIR / source["output"]
            output_path.write_bytes(ics_data)
            logger.info(f"[{name}] Wrote {len(events)} events to {output_path}")
            success_count += 1

        except Exception as e:
            logger.error(f"[{name}] Failed: {e}", exc_info=True)

    if success_count == 0:
        logger.error("All sources failed — aborting")
        return 1

    # Generate landing page
    landing = generate_landing_page(sources)
    (OUTPUT_DIR / "index.html").write_text(landing, encoding="utf-8")
    logger.info(f"Generated landing page at {OUTPUT_DIR / 'index.html'}")

    logger.info(f"Pipeline complete: {success_count}/{len(sources)} sources succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
