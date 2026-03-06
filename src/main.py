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
    """Generate an HTML landing page with calendar cards, copy buttons, and responsive layout."""
    cards = ""
    for source in sources:
        lang = "🇩🇪 DE" if source["language"] == "de" else "🇬🇧 EN"
        level = source.get("detail_level", "")
        level_desc = source.get("detail_description", "")
        badge_class = "badge-detailed" if level == "Detailed" else "badge-overview"
        cards += f"""
        <div class="card">
            <div class="card-header">
                <h2>{source['calendar_name']}</h2>
                <div class="card-badges">
                    <span class="badge {badge_class}">{level}</span>
                    <span class="badge badge-lang">{lang}</span>
                </div>
            </div>
            <p class="card-desc">{level_desc}</p>
            <div class="url-row">
                <code class="url-display" id="url-{source['output']}">{source['output']}</code>
                <a class="dl-btn" href="{source['output']}" download title="Download .ics file">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M2.75 14A1.75 1.75 0 011 12.25v-2.5a.75.75 0 011.5 0v2.5c0 .138.112.25.25.25h10.5a.25.25 0 00.25-.25v-2.5a.75.75 0 011.5 0v2.5A1.75 1.75 0 0113.25 14z"/>
                        <path d="M7.25 7.689V2a.75.75 0 011.5 0v5.689l1.97-1.969a.749.749 0 111.06 1.06l-3.25 3.25a.749.749 0 01-1.06 0L4.22 6.78a.749.749 0 111.06-1.06z"/>
                    </svg>
                    <span class="dl-label">Download</span>
                </a>
                <button class="copy-btn" onclick="copyUrl('{source['output']}')" title="Copy subscribe URL">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 010 1.5h-1.5a.25.25 0 00-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 00.25-.25v-1.5a.75.75 0 011.5 0v1.5A1.75 1.75 0 019.25 16h-7.5A1.75 1.75 0 010 14.25z"/>
                        <path d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0114.25 11h-7.5A1.75 1.75 0 015 9.25zm1.75-.25a.25.25 0 00-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 00.25-.25v-7.5a.25.25 0 00-.25-.25z"/>
                    </svg>
                    <span class="copy-label">Copy URL</span>
                </button>
            </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>HdM Calendars – ICS Subscribe</title>
    <meta name="description" content="Subscribe to HdM Stuttgart calendar events as ICS webcalendars. Auto-updated daily.">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 740px;
            margin: 0 auto;
            padding: 2rem 1rem;
            color: #1a1a1a;
            line-height: 1.6;
            background: #fafafa;
        }}

        header {{
            margin-bottom: 2rem;
        }}
        h1 {{
            font-size: 1.75rem;
            margin-bottom: 0.25rem;
        }}
        header p {{
            color: #555;
            font-size: 0.95rem;
        }}

        /* --- About section --- */
        .about {{
            background: #fff;
            border: 1px solid #e5e5e5;
            border-radius: 10px;
            padding: 1.25rem 1.5rem;
            margin-bottom: 1.5rem;
            font-size: 0.9rem;
            color: #444;
        }}
        .about strong {{ color: #1a1a1a; }}
        .about ul {{
            margin: 0.5rem 0 0 1.25rem;
            padding: 0;
        }}
        .about li {{ margin-bottom: 0.2rem; }}

        /* --- Cards --- */
        .card {{
            background: #fff;
            border: 1px solid #e5e5e5;
            border-radius: 10px;
            padding: 1.25rem 1.5rem;
            margin-bottom: 1rem;
            transition: box-shadow 0.15s;
        }}
        .card:hover {{
            box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 0.75rem;
            flex-wrap: wrap;
        }}
        .card-header h2 {{
            font-size: 1.1rem;
            font-weight: 600;
        }}
        .card-badges {{
            display: flex;
            gap: 0.4rem;
            flex-shrink: 0;
        }}
        .badge {{
            display: inline-block;
            font-size: 0.7rem;
            font-weight: 600;
            padding: 0.2em 0.6em;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            white-space: nowrap;
        }}
        .badge-detailed {{
            background: #e8f5e9;
            color: #2e7d32;
        }}
        .badge-overview {{
            background: #e3f2fd;
            color: #1565c0;
        }}
        .badge-lang {{
            background: #f5f5f5;
            color: #666;
        }}
        .card-desc {{
            font-size: 0.85rem;
            color: #777;
            margin: 0.4rem 0 0.75rem;
        }}

        /* --- URL row --- */
        .url-row {{
            display: flex;
            align-items: stretch;
            gap: 0;
            border: 1px solid #ddd;
            border-radius: 6px;
            overflow: hidden;
        }}
        .url-display {{
            flex: 1;
            padding: 0.5rem 0.75rem;
            font-size: 0.8rem;
            background: #f9f9f9;
            color: #333;
            overflow-x: auto;
            white-space: nowrap;
            border: none;
            display: flex;
            align-items: center;
        }}
        .copy-btn {{
            display: flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.5rem 0.85rem;
            background: #e2001a;
            color: #fff;
            border: none;
            cursor: pointer;
            font-size: 0.8rem;
            font-weight: 500;
            transition: background 0.15s;
            white-space: nowrap;
        }}
        .copy-btn:hover {{
            background: #b80015;
        }}
        .copy-btn.copied {{
            background: #2e7d32;
        }}

        .dl-btn {{
            display: flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.5rem 0.85rem;
            background: #f5f5f5;
            color: #333;
            border: none;
            border-left: 1px solid #ddd;
            cursor: pointer;
            font-size: 0.8rem;
            font-weight: 500;
            text-decoration: none;
            transition: background 0.15s;
            white-space: nowrap;
        }}
        .dl-btn:hover {{
            background: #e8e8e8;
            text-decoration: none;
        }}

        /* --- How-to --- */
        .how-to {{
            background: #fff;
            border: 1px solid #e5e5e5;
            border-radius: 10px;
            padding: 1rem 1.5rem;
            margin-top: 1.5rem;
            font-size: 0.88rem;
            color: #444;
        }}
        .how-to strong {{ color: #1a1a1a; }}
        .how-to ol {{
            margin: 0.5rem 0 0 1.25rem;
            padding: 0;
        }}
        .how-to li {{ margin-bottom: 0.2rem; }}

        footer {{
            margin-top: 2rem;
            font-size: 0.78rem;
            color: #aaa;
            text-align: center;
        }}
        footer a {{ color: #888; }}

        a {{ color: #e2001a; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}

        /* --- Mobile --- */
        @media (max-width: 500px) {{
            body {{ padding: 1rem 0.75rem; }}
            h1 {{ font-size: 1.4rem; }}
            .card {{ padding: 1rem; }}
            .card-header {{ flex-direction: column; gap: 0.4rem; }}
            .copy-label, .dl-label {{ display: none; }}
            .copy-btn, .dl-btn {{ padding: 0.5rem 0.65rem; }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>📅 HdM Stuttgart Calendars</h1>
        <p>Subscribable webcalendars from <a href="https://www.hdm-stuttgart.de">hdm-stuttgart.de</a></p>
    </header>

    <div class="about">
        <strong>What is this?</strong> This page provides subscribable calendar files (.ics) generated
        automatically from the official HdM Stuttgart calendar pages. Once you subscribe, your calendar
        app will always stay up-to-date.
        <ul>
            <li>🔄 <strong>Auto-refreshes daily</strong> at 06:00 UTC via GitHub Actions</li>
            <li>📆 Works with Google Calendar, Apple Calendar, Outlook, and any app that supports ICS</li>
            <li>🔗 Just copy the URL below and add it as a calendar subscription</li>
        </ul>
    </div>
    {cards}

    <div class="how-to">
        <strong>How to subscribe:</strong>
        <ol>
            <li>Click <strong>Copy</strong> next to the calendar you want</li>
            <li>Open your calendar app (Google Calendar, Apple Calendar, Outlook, …)</li>
            <li>Choose <em>"Add calendar → From URL"</em> and paste the link</li>
            <li>Done — the calendar will auto-update daily</li>
        </ol>
    </div>

    <footer>
        Auto-updated daily via GitHub Actions ·
        <a href="https://github.com/julian-schn/hdm-calendars-ics">Source on GitHub</a>
    </footer>

    <script>
    function copyUrl(filename) {{
        const fullUrl = window.location.href.replace(/\\/[^/]*$/, '/') + filename;
        navigator.clipboard.writeText(fullUrl).then(() => {{
            const btn = event.currentTarget;
            const label = btn.querySelector('.copy-label');
            btn.classList.add('copied');
            if (label) label.textContent = 'Copied!';
            setTimeout(() => {{
                btn.classList.remove('copied');
                if (label) label.textContent = 'Copy';
            }}, 2000);
        }});
    }}
    </script>
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
