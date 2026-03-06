#!/usr/bin/env python3
"""
HdM Calendars → ICS Pipeline

Reads source configurations, crawls each calendar page,
generates ICS files, and writes them to the output directory.
"""

import html
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
    """Generate a simple, consistent HTML landing page for calendar subscriptions."""
    rows = ""
    for source in sources:
        language = "DE" if source["language"] == "de" else "EN"
        level = html.escape(source.get("detail_level", "Standard"))
        description = html.escape(source.get("detail_description", ""))
        coverage = level if not description else f"{level}: {description}"
        calendar_name = html.escape(source["calendar_name"])
        output_file = html.escape(source["output"])
        output_js = json.dumps(source["output"])

        rows += f"""
        <tr>
            <td>{calendar_name}</td>
            <td>{language}</td>
            <td>{coverage}</td>
            <td class="subscribe-cell">
                <div class="sub-actions">
                    <a class="ics-link" href="{output_file}">{output_file}</a>
                    <button type="button" class="copy-btn" onclick='copyUrl({output_js}, this)'>Copy URL</button>
                    <a class="download-link" href="{output_file}" download>Download</a>
                </div>
                <div class="copy-status" aria-live="polite"></div>
            </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>HdM Calendars – ICS Subscribe</title>
    <meta name="description" content="Subscribe to HdM Stuttgart calendar events as ICS webcalendars. Auto-updated daily.">
    <style>
        :root {{
            --accent: #b00014;
            --accent-strong: #8a0010;
            --accent-soft: #fdecef;
            --text: #1a1a1a;
            --muted: #555;
            --line: #e6e8ee;
            --panel-bg: #ffffff;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem 1rem;
            color: var(--text);
            line-height: 1.5;
            background: linear-gradient(180deg, #f6f8fc 0%, #ffffff 45%);
        }}
        a {{ color: var(--accent); text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        h1 {{
            margin: 0 0 0.4rem;
            font-size: 1.6rem;
            color: var(--accent-strong);
            letter-spacing: 0.01em;
        }}
        p.subtitle {{
            margin: 0 0 1.25rem;
            color: var(--muted);
            font-size: 0.95rem;
        }}
        .panel {{
            border: 1px solid #e2d5d8;
            border-radius: 10px;
            overflow: hidden;
            background: var(--panel-bg);
            box-shadow: 0 8px 24px rgba(17, 24, 39, 0.05);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            text-align: left;
            padding: 0.75rem;
            border-bottom: 1px solid var(--line);
            vertical-align: top;
            font-size: 0.92rem;
        }}
        th {{
            background: #fff4f6;
            font-weight: 600;
            color: #3a1c21;
        }}
        tbody tr:nth-child(even) {{
            background: #fcfcfd;
        }}
        tbody tr:hover {{
            background: #f7f9ff;
        }}
        td:nth-child(2), th:nth-child(2) {{
            width: 4rem;
            white-space: nowrap;
            font-weight: 600;
        }}
        td:nth-child(4), th:nth-child(4) {{
            width: 18rem;
        }}
        .subscribe-cell {{
            min-width: 18rem;
        }}
        .sub-actions {{
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.45rem;
        }}
        .ics-link {{
            word-break: break-all;
        }}
        .copy-btn, .download-link {{
            border: 1px solid #d8dbe3;
            border-radius: 6px;
            padding: 0.3rem 0.55rem;
            font-size: 0.8rem;
            line-height: 1.2;
            background: #fff;
            color: #333;
            text-decoration: none;
            transition: transform 0.05s ease, background 0.2s ease, border-color 0.2s ease;
        }}
        .copy-btn {{
            cursor: pointer;
            background: var(--accent);
            color: #fff;
            border-color: var(--accent);
        }}
        .copy-btn:hover, .download-link:hover {{
            background: #f3f3f3;
            text-decoration: none;
        }}
        .copy-btn:hover {{
            background: var(--accent-strong);
            border-color: var(--accent-strong);
        }}
        .copy-btn:active, .download-link:active {{
            transform: translateY(1px);
        }}
        .copy-btn.copied {{
            border-color: #2e7d32;
            background: #2e7d32;
            color: #fff;
        }}
        .copy-status {{
            margin-top: 0.35rem;
            font-size: 0.78rem;
            color: #666;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        .how-to {{
            margin-top: 1rem;
            padding: 0.9rem 1rem;
            background: #f7fbff;
            border: 1px solid #d7e7f8;
            border-left: 4px solid #5d8fd3;
            border-radius: 8px;
            font-size: 0.9rem;
        }}
        .how-to ol {{
            margin: 0.5rem 0 0 1.2rem;
            padding: 0;
        }}
        .how-to li {{
            margin: 0.25rem 0;
        }}
        .what-is-this {{
            margin-top: 1rem;
            padding: 0.9rem 1rem;
            background: #fff8f8;
            border: 1px solid #f1dadd;
            border-left: 4px solid var(--accent);
            border-radius: 8px;
            font-size: 0.9rem;
        }}
        .what-is-this p {{
            margin: 0.4rem 0 0;
            color: #555;
        }}
        .what-is-this ul {{
            margin: 0.55rem 0 0 1.2rem;
            padding: 0;
        }}
        .what-is-this li {{
            margin: 0.25rem 0;
        }}
        footer {{
            margin-top: 1rem;
            color: #6f7481;
            font-size: 0.8rem;
            border-top: 1px solid var(--line);
            padding-top: 0.8rem;
        }}
        @media (max-width: 760px) {{
            td:nth-child(4), th:nth-child(4) {{
                width: auto;
            }}
        }}
    </style>
</head>
<body>
    <h1>HdM Stuttgart Calendars</h1>
    <p class="subtitle">Subscribable ICS calendars generated from <a href="https://www.hdm-stuttgart.de">hdm-stuttgart.de</a>.</p>

    <div class="panel">
        <table>
            <thead>
                <tr>
                    <th>Calendar</th>
                    <th>Lang</th>
                    <th>Coverage</th>
                    <th>ICS URL</th>
                </tr>
            </thead>
            <tbody>{rows}
            </tbody>
        </table>
    </div>

    <div class="how-to">
        <strong>How to subscribe</strong>
        <ol>
            <li>Copy an ICS URL from the table.</li>
            <li>In your calendar app, choose <em>Add calendar → From URL</em>.</li>
            <li>Paste the URL to keep events automatically up to date.</li>
        </ol>
    </div>

    <div class="what-is-this">
        <strong>What is this?</strong>
        <p>These are auto-generated ICS feeds from official HdM calendar pages.</p>
        <ul>
            <li><strong>Subscribe by URL</strong> to get daily updates automatically.</li>
            <li><strong>Download</strong> is only a one-time snapshot that does not sync future changes.</li>
            <li>Use download only for one-off import, offline use, or archiving.</li>
        </ul>
    </div>

    <footer>
        Updated daily at 06:00 UTC via GitHub Actions ·
        <a href="https://schniepp.dev">Maintained by Julian Schniepp</a> ·
        <a href="https://github.com/julian-schn/hdm-calendars-ics">Source</a>
    </footer>

    <script>
    function copyUrl(filename, button) {{
        const pageUrl = window.location.href.replace(/\\/[^/]*$/, '/');
        const fullUrl = new URL(filename, pageUrl).toString();
        const status = button.closest('.subscribe-cell').querySelector('.copy-status');
        const originalLabel = button.dataset.label || button.textContent;
        button.dataset.label = originalLabel;

        navigator.clipboard.writeText(fullUrl).then(() => {{
            button.textContent = 'Copied';
            button.classList.add('copied');
            if (status) status.textContent = fullUrl;
            setTimeout(() => {{
                button.textContent = originalLabel;
                button.classList.remove('copied');
            }}, 1800);
        }}).catch(() => {{
            if (status) status.textContent = 'Copy failed. Please copy the URL manually.';
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
