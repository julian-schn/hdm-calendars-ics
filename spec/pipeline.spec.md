# Pipeline Specification

## Purpose
Orchestrate the crawl → generate → output flow for all configured calendar sources.

## Trigger
- **Scheduled:** Daily at 06:00 UTC via GitHub Actions cron
- **Manual:** `workflow_dispatch` from GitHub Actions UI
- **On push:** Any push to `main` branch (for development/testing)

## Pipeline Steps

### 1. Load Configuration
- Read `config/sources.json`
- Validate each source entry has required fields: `name`, `url`, `output`, `calendar_name`, `language`

### 2. Crawl Each Source
- For each source in config, run the crawler (see `crawl.spec.md`)
- Sources are processed sequentially to avoid overwhelming the target server
- Log the number of events found per source

### 3. Generate ICS Files
- For each source, generate an `.ics` file from the crawled events (see `ics-generate.spec.md`)
- Write files to `dist/` directory

### 4. Generate Landing Page
- Copy or generate `dist/index.html` with current calendar links

### 5. Deploy (GitHub Actions only)
- Upload `dist/` as a GitHub Pages artifact
- Deploy to GitHub Pages

## Output
```
dist/
├── index.html
├── hdm-termine.ics
├── hdm-akademisch.ics
└── hdm-academic-en.ics
```

## Error Policy
- If a single source fails, log the error and continue with remaining sources
- If all sources fail, exit with non-zero code (triggers GitHub Actions failure notification)
- Never deploy an empty `dist/` (at least one `.ics` must be generated)

## Logging
- Log to stdout (captured by GitHub Actions)
- Format: `[SOURCE_NAME] message`
- Log levels: INFO for progress, WARNING for skipped events, ERROR for failures
