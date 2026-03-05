# HdM Calendars → ICS

[![Build & Deploy](https://github.com/julian-schn/hdm-calendars-ics/actions/workflows/build.yml/badge.svg)](https://github.com/julian-schn/hdm-calendars-ics/actions/workflows/build.yml)

Automatically crawls [HdM Stuttgart](https://www.hdm-stuttgart.de) calendar pages daily and publishes subscribable `.ics` webcalendars via GitHub Pages.

## 📅 Subscribe

| Calendar | Language | Details | Subscribe |
|----------|----------|---------|-----------|
| HdM Terminkalender | 🇩🇪 DE | Detailed — includes times, locations, and descriptions | `https://julian-schn.github.io/hdm-calendars-ics/hdm-termine.ics` |
| HdM Akademischer Kalender | 🇩🇪 DE | Overview — semester milestones and key dates only | `https://julian-schn.github.io/hdm-calendars-ics/hdm-akademisch.ics` |
| HdM Academic Calendar | 🇬🇧 EN | Overview — semester milestones and key dates only | `https://julian-schn.github.io/hdm-calendars-ics/hdm-academic-en.ics` |

> Copy the URL and add it as a "subscription" / "From URL" calendar in Google Calendar, Apple Calendar, or Outlook.

## How It Works

1. **GitHub Actions** runs a scheduled workflow daily at 06:00 UTC
2. A Python script crawls the HdM calendar webpages
3. Events are parsed and converted to `.ics` (iCalendar) format
4. The `.ics` files are deployed to **GitHub Pages**
5. Anyone can subscribe to the calendar URL — it auto-updates daily

## Sources

Sources are defined in [`config/sources.json`](config/sources.json). Each source specifies:
- `url` — the webpage to crawl
- `output` — the `.ics` filename to generate
- `language` — `de` or `en` (affects date parsing)
- `follow_detail_links` — whether to follow event links for full details

## Specs

This project uses **spec-driven development**. Behavior specifications live in [`spec/`](spec/):
- [`crawl.spec.md`](spec/crawl.spec.md) — crawler behavior
- [`ics-generate.spec.md`](spec/ics-generate.spec.md) — ICS generation rules
- [`pipeline.spec.md`](spec/pipeline.spec.md) — end-to-end pipeline

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the pipeline
python src/main.py

# Output is written to dist/
ls dist/*.ics
```

## Project Structure

```
├── .github/workflows/build.yml   # CI/CD: crawl → generate → deploy
├── config/sources.json            # Data source definitions
├── spec/                          # Behavior specifications
├── src/
│   ├── crawl.py                   # HTML → structured events
│   ├── generate_ics.py            # Events → ICS file
│   └── main.py                    # Orchestrator
├── dist/                          # Generated output (deployed to Pages)
└── requirements.txt
```

## License

MIT
