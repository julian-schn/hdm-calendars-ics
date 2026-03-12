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
        copy_label = html.escape(f"Copy subscription URL for {source['calendar_name']}", quote=True)
        download_label = html.escape(f"Download ICS file for {source['calendar_name']}", quote=True)

        rows += f"""
        <tr>
            <td>{calendar_name}</td>
            <td>{language}</td>
            <td>{coverage}</td>
            <td class="subscribe-cell">
                <div class="sub-actions">
                    <a class="ics-link" href="{output_file}">{output_file}</a>
                    <button type="button" class="copy-btn" onclick='copyUrl({output_js}, this)' aria-label="{copy_label}">Copy URL</button>
                    <a class="download-link" href="{output_file}" download aria-label="{download_label}">Download</a>
                </div>
                <div class="copy-status" aria-live="polite"></div>
            </td>
        </tr>"""

    calendar_options = ""
    for source in sources:
        cal_name = html.escape(source["calendar_name"])
        output_file = html.escape(source["output"])
        calendar_options += f'                <option value="{output_file}">{cal_name}</option>\n'

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
        a:focus-visible, button:focus-visible {{
            outline: 3px solid #1f6feb;
            outline-offset: 2px;
            border-radius: 6px;
        }}
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
            overflow-x: auto;
            overflow-y: hidden;
            background: var(--panel-bg);
            box-shadow: 0 8px 24px rgba(17, 24, 39, 0.05);
        }}
        caption {{
            caption-side: top;
            text-align: left;
            padding: 0.75rem;
            font-weight: 600;
            color: #2f3b52;
            background: #f8fbff;
            border-bottom: 1px solid var(--line);
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
            min-width: 0;
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
        .section-title {{
            margin: 0;
            font-size: 1rem;
            color: #223047;
        }}
        footer {{
            margin-top: 1rem;
            color: #6f7481;
            font-size: 0.8rem;
            border-top: 1px solid var(--line);
            padding-top: 0.8rem;
        }}
        .calendar-preview {{
            margin-top: 1rem;
            overflow: visible;
        }}
        .preview-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 0.5rem;
            padding: 0.75rem 1rem;
            background: #f8fbff;
            border-bottom: 1px solid var(--line);
        }}
        .preview-controls {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            flex-wrap: wrap;
        }}
        #calendarSelect {{
            padding: 0.35rem 0.5rem;
            border: 1px solid #d8dbe3;
            border-radius: 6px;
            font-size: 0.85rem;
            background: #fff;
            color: var(--text);
            cursor: pointer;
        }}
        .month-nav {{
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }}
        .month-nav button {{
            border: 1px solid #d8dbe3;
            border-radius: 6px;
            padding: 0.3rem 0.55rem;
            font-size: 0.85rem;
            background: #fff;
            color: var(--text);
            cursor: pointer;
            line-height: 1.2;
        }}
        .month-nav button:hover {{
            background: #f3f3f3;
        }}
        .month-nav button:active {{
            transform: translateY(1px);
        }}
        .today-btn {{
            font-size: 0.78rem !important;
            color: var(--accent) !important;
            border-color: var(--accent) !important;
        }}
        #monthLabel {{
            font-weight: 600;
            font-size: 0.95rem;
            min-width: 9rem;
            text-align: center;
        }}
        .month-grid {{
            display: grid;
            grid-template-columns: repeat(7, minmax(0, 1fr));
        }}
        .day-header {{
            padding: 0.4rem 0.3rem;
            text-align: center;
            font-weight: 600;
            font-size: 0.75rem;
            color: var(--muted);
            background: #fafbfd;
            border-bottom: 1px solid var(--line);
        }}
        .day-cell {{
            min-height: 5rem;
            padding: 0.3rem;
            border-bottom: 1px solid var(--line);
            border-right: 1px solid var(--line);
            font-size: 0.8rem;
        }}
        .day-cell:nth-child(7n+7) {{
            border-right: none;
        }}
        .day-cell.outside {{
            background: #f9fafb;
            color: #bbb;
        }}
        .day-cell.today {{
            background: var(--accent-soft);
        }}
        .day-number {{
            font-weight: 600;
            font-size: 0.8rem;
            margin-bottom: 0.15rem;
        }}
        .day-cell.today .day-number {{
            color: var(--accent);
        }}
        .day-event {{
            display: block;
            padding: 0.1rem 0.25rem;
            margin-bottom: 0.15rem;
            border-radius: 3px;
            font-size: 0.7rem;
            line-height: 1.3;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            background: var(--accent-soft);
            color: var(--accent-strong);
            border-left: 2px solid var(--accent);
            cursor: pointer;
        }}
        .day-event:hover {{
            background: #f9d4d9;
        }}
        .day-event.multi-day {{
            border-left-color: #5d8fd3;
            background: #e8f0fe;
            color: #1a4d8f;
        }}
        .day-event.multi-day:hover {{
            background: #d4e4fc;
        }}
        .day-more {{
            font-size: 0.68rem;
            color: var(--muted);
            padding: 0.1rem 0.25rem;
            cursor: pointer;
        }}
        .day-more:hover {{
            color: var(--accent);
        }}
        .agenda-list {{
            display: none;
            padding: 0.5rem 1rem;
        }}
        .agenda-item {{
            display: flex;
            gap: 0.75rem;
            padding: 0.6rem 0;
            border-bottom: 1px solid var(--line);
            font-size: 0.88rem;
            cursor: pointer;
        }}
        .agenda-item:last-child {{
            border-bottom: none;
        }}
        .agenda-item:hover {{
            background: #f7f9ff;
        }}
        .agenda-date {{
            min-width: 3.5rem;
            font-weight: 600;
            color: var(--accent);
            text-align: right;
            font-size: 0.82rem;
            line-height: 1.4;
        }}
        .agenda-info {{
            flex: 1;
            min-width: 0;
        }}
        .agenda-title {{
            font-weight: 500;
        }}
        .agenda-meta {{
            font-size: 0.78rem;
            color: var(--muted);
            margin-top: 0.15rem;
        }}
        .agenda-empty {{
            padding: 1.5rem;
            text-align: center;
            color: var(--muted);
            font-size: 0.9rem;
        }}
        .event-detail {{
            padding: 0.75rem 1rem;
            background: #fffbf0;
            border-top: 2px solid var(--accent);
            font-size: 0.88rem;
        }}
        .event-detail h3 {{
            margin: 0 0 0.4rem;
            font-size: 0.95rem;
            color: var(--accent-strong);
        }}
        .event-detail p {{
            margin: 0.2rem 0;
            color: var(--muted);
            font-size: 0.82rem;
        }}
        .event-detail a {{
            font-size: 0.82rem;
        }}
        .event-detail-close {{
            float: right;
            border: none;
            background: none;
            font-size: 1.1rem;
            cursor: pointer;
            color: var(--muted);
            padding: 0;
            line-height: 1;
        }}
        .calendar-loading {{
            padding: 2rem;
            text-align: center;
            color: var(--muted);
            font-size: 0.9rem;
        }}
        .calendar-error {{
            padding: 1rem;
            text-align: center;
            color: #c0392b;
            font-size: 0.88rem;
            background: #fff5f5;
        }}
        @media (max-width: 760px) {{
            td:nth-child(4), th:nth-child(4) {{
                width: auto;
            }}
            .sub-actions {{
                flex-direction: column;
                align-items: flex-start;
            }}
            .month-grid {{
                display: none;
            }}
            .agenda-list {{
                display: block;
            }}
            .preview-header {{
                flex-direction: column;
                align-items: flex-start;
            }}
            .preview-controls {{
                width: 100%;
            }}
            #calendarSelect {{
                width: 100%;
            }}
            .month-nav {{
                width: 100%;
                justify-content: space-between;
            }}
        }}
    </style>
</head>
<body>
    <h1>HdM Stuttgart Calendars</h1>
    <p class="subtitle">Subscribable ICS calendars generated from <a href="https://www.hdm-stuttgart.de">hdm-stuttgart.de</a>.</p>
    <main>
    <div class="panel">
        <table>
            <caption>Available HdM calendar subscriptions</caption>
            <thead>
                <tr>
                    <th scope="col">Calendar</th>
                    <th scope="col">Lang</th>
                    <th scope="col">Coverage</th>
                    <th scope="col">ICS URL</th>
                </tr>
            </thead>
            <tbody>{rows}
            </tbody>
        </table>
    </div>

    <div class="calendar-preview panel">
        <div class="preview-header">
            <h2 class="section-title">Calendar Preview</h2>
            <div class="preview-controls">
                <select id="calendarSelect" aria-label="Choose calendar to preview">
{calendar_options}                </select>
                <div class="month-nav">
                    <button type="button" id="prevMonth" aria-label="Previous month">&larr;</button>
                    <span id="monthLabel"></span>
                    <button type="button" id="nextMonth" aria-label="Next month">&rarr;</button>
                    <button type="button" id="todayBtn" class="today-btn">Today</button>
                </div>
            </div>
        </div>
        <div id="calendarLoading" class="calendar-loading" aria-live="polite">Loading events…</div>
        <div id="calendarError" class="calendar-error" hidden aria-live="polite"></div>
        <div id="monthGrid" class="month-grid" role="grid" aria-label="Calendar month view"></div>
        <div id="agendaList" class="agenda-list" role="list" aria-label="Upcoming events list"></div>
        <div id="eventDetail" class="event-detail" hidden></div>
    </div>

    <div class="how-to">
        <h2 class="section-title">How to subscribe</h2>
        <ol>
            <li>Copy an ICS URL from the table.</li>
            <li>In your calendar app, choose <em>Add calendar → From URL</em>.</li>
            <li>Paste the URL to keep events automatically up to date.</li>
        </ol>
    </div>

    <div class="what-is-this">
        <h2 class="section-title">What is this?</h2>
        <p>These are auto-generated ICS feeds from official HdM calendar pages.</p>
        <ul>
            <li><strong>Subscribe by URL</strong> to get daily updates automatically.</li>
            <li><strong>Download</strong> is only a one-time snapshot that does not sync future changes.</li>
            <li>Use download only for one-off import, offline use, or archiving.</li>
        </ul>
    </div>
    </main>

    <footer>
        Updated twice daily at 05:00 and 18:00 CET via GitHub Actions ·
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

    // --- Calendar Preview ---
    const calendarCache = {{}};
    let currentYear, currentMonth, currentEvents = [];

    function unfoldICS(text) {{
        return text.replace(/\\r\\n[ \\t]/g, '').replace(/\\n[ \\t]/g, '');
    }}

    function parseDTValue(key, value) {{
        if (key.includes('VALUE=DATE') && value.length === 8) {{
            return new Date(parseInt(value.substring(0,4)), parseInt(value.substring(4,6))-1, parseInt(value.substring(6,8)));
        }}
        if (value.includes('T')) {{
            return new Date(parseInt(value.substring(0,4)), parseInt(value.substring(4,6))-1, parseInt(value.substring(6,8)),
                parseInt(value.substring(9,11)), parseInt(value.substring(11,13)));
        }}
        return new Date(parseInt(value.substring(0,4)), parseInt(value.substring(4,6))-1, parseInt(value.substring(6,8)));
    }}

    function parseICS(text) {{
        const unfolded = unfoldICS(text);
        const lines = unfolded.split(/\\r?\\n/);
        const events = [];
        let cur = null;
        for (const line of lines) {{
            if (line === 'BEGIN:VEVENT') {{ cur = {{}}; continue; }}
            if (line === 'END:VEVENT') {{
                if (cur && cur.dtstart) events.push(cur);
                cur = null; continue;
            }}
            if (!cur) continue;
            const ci = line.indexOf(':');
            if (ci < 0) continue;
            const key = line.substring(0, ci), val = line.substring(ci + 1);
            if (key === 'SUMMARY') cur.summary = val;
            else if (key.startsWith('DTSTART')) {{
                cur.dtstart = parseDTValue(key, val);
                cur.allDay = key.includes('VALUE=DATE') && !key.includes('VALUE=DATE-TIME');
            }}
            else if (key.startsWith('DTEND')) cur.dtend = parseDTValue(key, val);
            else if (key === 'LOCATION') cur.location = val;
            else if (key === 'URL') cur.url = val;
            else if (key === 'DESCRIPTION') cur.description = val.replace(/\\\\n/g, '\\n').replace(/\\\\,/g, ',');
        }}
        return events;
    }}

    async function loadCalendar(filename) {{
        if (calendarCache[filename]) return calendarCache[filename];
        const resp = await fetch(filename);
        if (!resp.ok) throw new Error(resp.status);
        const text = await resp.text();
        const events = parseICS(text);
        calendarCache[filename] = events;
        return events;
    }}

    function dateKey(d) {{
        return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
    }}

    function isMultiDay(evt) {{
        if (!evt.dtend) return false;
        const s = new Date(evt.dtstart.getFullYear(), evt.dtstart.getMonth(), evt.dtstart.getDate()).getTime();
        const e = evt.allDay
            ? new Date(evt.dtend.getTime() - 86400000)
            : evt.dtend;
        return new Date(e.getFullYear ? e.getFullYear() : e, e.getMonth ? e.getMonth() : 0, e.getDate ? e.getDate() : 1).getTime() > s;
    }}

    function getEventsForDate(date) {{
        const dayStart = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
        const dayEnd = dayStart + 86400000;
        return currentEvents.filter(evt => {{
            const evtStart = evt.dtstart.getTime();
            const evtEnd = evt.dtend ? evt.dtend.getTime() : evtStart + 86400000;
            return evtStart < dayEnd && evtEnd > dayStart;
        }});
    }}

    function escapeHtml(s) {{
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }}

    function updateMonthLabel() {{
        const names = ['January','February','March','April','May','June','July','August','September','October','November','December'];
        document.getElementById('monthLabel').textContent = names[currentMonth] + ' ' + currentYear;
    }}

    function renderMonthGrid() {{
        const grid = document.getElementById('monthGrid');
        grid.innerHTML = '';
        const dayNames = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
        dayNames.forEach(n => {{
            const el = document.createElement('div');
            el.className = 'day-header';
            el.textContent = n;
            grid.appendChild(el);
        }});

        const firstDay = new Date(currentYear, currentMonth, 1);
        const lastDay = new Date(currentYear, currentMonth + 1, 0);
        const startDow = (firstDay.getDay() + 6) % 7;
        const todayStr = dateKey(new Date());
        const prevLast = new Date(currentYear, currentMonth, 0);

        for (let i = startDow - 1; i >= 0; i--) {{
            grid.appendChild(makeDayCell(prevLast.getDate() - i, true, null, false));
        }}
        for (let d = 1; d <= lastDay.getDate(); d++) {{
            const cellDate = new Date(currentYear, currentMonth, d);
            const isToday = dateKey(cellDate) === todayStr;
            grid.appendChild(makeDayCell(d, false, getEventsForDate(cellDate), isToday));
        }}
        const total = startDow + lastDay.getDate();
        const trailing = (7 - (total % 7)) % 7;
        for (let d = 1; d <= trailing; d++) {{
            grid.appendChild(makeDayCell(d, true, null, false));
        }}
    }}

    function makeDayCell(dayNum, isOutside, events, isToday) {{
        const cell = document.createElement('div');
        cell.className = 'day-cell' + (isOutside ? ' outside' : '') + (isToday ? ' today' : '');
        const num = document.createElement('div');
        num.className = 'day-number';
        num.textContent = dayNum;
        cell.appendChild(num);
        if (events && events.length > 0) {{
            const max = 2;
            events.slice(0, max).forEach(evt => {{
                const tag = document.createElement('div');
                tag.className = 'day-event' + (isMultiDay(evt) ? ' multi-day' : '');
                tag.textContent = evt.summary || '(No title)';
                tag.title = evt.summary || '';
                tag.addEventListener('click', e => {{ e.stopPropagation(); showEventDetail(evt); }});
                cell.appendChild(tag);
            }});
            if (events.length > max) {{
                const more = document.createElement('div');
                more.className = 'day-more';
                more.textContent = '+' + (events.length - max) + ' more';
                more.addEventListener('click', e => {{
                    e.stopPropagation();
                    showAllDayEvents(events);
                }});
                cell.appendChild(more);
            }}
        }}
        return cell;
    }}

    function renderAgendaList() {{
        const list = document.getElementById('agendaList');
        list.innerHTML = '';
        const mStart = new Date(currentYear, currentMonth, 1);
        const mEnd = new Date(currentYear, currentMonth + 1, 0, 23, 59, 59);
        const monthEvents = currentEvents.filter(evt => {{
            const evtEnd = evt.dtend ? evt.dtend.getTime() : evt.dtstart.getTime() + 86400000;
            return evt.dtstart.getTime() <= mEnd.getTime() && evtEnd > mStart.getTime();
        }}).sort((a, b) => a.dtstart - b.dtstart);

        if (monthEvents.length === 0) {{
            const empty = document.createElement('div');
            empty.className = 'agenda-empty';
            empty.textContent = 'No events this month.';
            list.appendChild(empty);
            return;
        }}
        const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        monthEvents.forEach(evt => {{
            const item = document.createElement('div');
            item.className = 'agenda-item';
            item.addEventListener('click', () => showEventDetail(evt));
            const dateDiv = document.createElement('div');
            dateDiv.className = 'agenda-date';
            dateDiv.innerHTML = evt.dtstart.getDate() + '<br>' + months[evt.dtstart.getMonth()];
            const infoDiv = document.createElement('div');
            infoDiv.className = 'agenda-info';
            const titleDiv = document.createElement('div');
            titleDiv.className = 'agenda-title';
            titleDiv.textContent = evt.summary || '(No title)';
            infoDiv.appendChild(titleDiv);
            const parts = [];
            if (isMultiDay(evt)) {{
                const opts = {{ month: 'short', day: 'numeric' }};
                let range = evt.dtstart.toLocaleDateString('en-US', opts);
                if (evt.dtend) {{
                    const endD = evt.allDay ? new Date(evt.dtend.getTime() - 86400000) : evt.dtend;
                    range += ' – ' + endD.toLocaleDateString('en-US', opts);
                }}
                parts.push(range);
            }}
            if (evt.location) parts.push(evt.location);
            if (parts.length) {{
                const meta = document.createElement('div');
                meta.className = 'agenda-meta';
                meta.textContent = parts.join(' · ');
                infoDiv.appendChild(meta);
            }}
            item.appendChild(dateDiv);
            item.appendChild(infoDiv);
            list.appendChild(item);
        }});
    }}

    function showEventDetail(evt) {{
        const detail = document.getElementById('eventDetail');
        let h = '<button class="event-detail-close" aria-label="Close detail">&times;</button>';
        h += '<h3>' + escapeHtml(evt.summary || 'Event') + '</h3>';
        const opts = {{ weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }};
        let dateLine = evt.dtstart.toLocaleDateString('en-US', opts);
        if (isMultiDay(evt) && evt.dtend) {{
            const endD = evt.allDay ? new Date(evt.dtend.getTime() - 86400000) : evt.dtend;
            dateLine += ' – ' + endD.toLocaleDateString('en-US', opts);
        }}
        if (!evt.allDay && evt.dtstart.getHours() !== 0) {{
            dateLine += ', ' + evt.dtstart.toLocaleTimeString('en-US', {{ hour: '2-digit', minute: '2-digit' }});
            if (evt.dtend) dateLine += ' – ' + evt.dtend.toLocaleTimeString('en-US', {{ hour: '2-digit', minute: '2-digit' }});
        }}
        h += '<p>' + escapeHtml(dateLine) + '</p>';
        if (evt.location) h += '<p>Location: ' + escapeHtml(evt.location) + '</p>';
        if (evt.description) h += '<p>' + escapeHtml(evt.description).substring(0, 300) + '</p>';
        if (evt.url) h += '<p><a href="' + escapeHtml(evt.url) + '" target="_blank" rel="noopener">More details &rarr;</a></p>';
        detail.innerHTML = h;
        detail.hidden = false;
        detail.querySelector('.event-detail-close').addEventListener('click', hideEventDetail);
        detail.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
    }}

    function showAllDayEvents(events) {{
        const detail = document.getElementById('eventDetail');
        let h = '<button class="event-detail-close" aria-label="Close detail">&times;</button>';
        events.forEach(evt => {{
            h += '<div class="day-event" style="cursor:pointer;margin:0.3rem 0;white-space:normal;">' + escapeHtml(evt.summary || '(No title)') + '</div>';
        }});
        detail.innerHTML = h;
        detail.hidden = false;
        detail.querySelector('.event-detail-close').addEventListener('click', hideEventDetail);
        detail.querySelectorAll('.day-event').forEach((el, i) => {{
            el.addEventListener('click', () => showEventDetail(events[i]));
        }});
    }}

    function hideEventDetail() {{
        document.getElementById('eventDetail').hidden = true;
    }}

    function renderCurrentView() {{
        updateMonthLabel();
        renderMonthGrid();
        renderAgendaList();
        hideEventDetail();
    }}

    async function onCalendarChange() {{
        const filename = document.getElementById('calendarSelect').value;
        const loading = document.getElementById('calendarLoading');
        const error = document.getElementById('calendarError');
        loading.hidden = false;
        error.hidden = true;
        document.getElementById('monthGrid').innerHTML = '';
        document.getElementById('agendaList').innerHTML = '';
        hideEventDetail();
        try {{
            currentEvents = await loadCalendar(filename);
            loading.hidden = true;
            renderCurrentView();
        }} catch (e) {{
            loading.hidden = true;
            error.textContent = 'Could not load calendar. Please try again.';
            error.hidden = false;
        }}
    }}

    document.addEventListener('DOMContentLoaded', () => {{
        const now = new Date();
        currentYear = now.getFullYear();
        currentMonth = now.getMonth();
        document.getElementById('calendarSelect').addEventListener('change', onCalendarChange);
        document.getElementById('prevMonth').addEventListener('click', () => {{
            currentMonth--;
            if (currentMonth < 0) {{ currentMonth = 11; currentYear--; }}
            renderCurrentView();
        }});
        document.getElementById('nextMonth').addEventListener('click', () => {{
            currentMonth++;
            if (currentMonth > 11) {{ currentMonth = 0; currentYear++; }}
            renderCurrentView();
        }});
        document.getElementById('todayBtn').addEventListener('click', () => {{
            currentYear = new Date().getFullYear();
            currentMonth = new Date().getMonth();
            renderCurrentView();
        }});
        onCalendarChange();
    }});
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
