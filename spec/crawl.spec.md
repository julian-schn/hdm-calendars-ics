# Crawl Specification

## Purpose
Fetch an HdM calendar webpage and extract structured event data from the HTML.

## Input
- `url` (string): The webpage URL to crawl
- `language` (string): `"de"` or `"en"` — affects date parsing
- `follow_detail_links` (bool): Whether to follow `/termin/...` links for full event details

## Output
A list of event dictionaries, each containing:

| Field         | Type            | Required | Description                        |
|---------------|-----------------|----------|------------------------------------|
| `title`       | `str`           | ✅       | Event name from `<h3>`             |
| `date_start`  | `date`          | ✅       | Start date                         |
| `date_end`    | `date \| None`  | ❌       | End date (if range)                |
| `time_start`  | `time \| None`  | ❌       | Start time (from detail page)      |
| `time_end`    | `time \| None`  | ❌       | End time (from detail page)        |
| `location`    | `str \| None`   | ❌       | Location (from detail page)        |
| `description` | `str \| None`   | ❌       | Full text (from detail page)       |
| `url`         | `str \| None`   | ❌       | Link to event detail page          |

## HTML Parsing Rules

### Listing Page (all 3 sources)
1. Find all event containers: elements containing a date display + title
2. Extract the **date** from the date display element (day number + month abbreviation)
3. Extract the **title** from the heading element
4. Extract the **detail link** URL if present
5. Extract inline **date/time/location** from meta elements with icon indicators

### Detail Page (when `follow_detail_links: true`)
1. Navigate to event URL
2. Extract **date** from sidebar calendar-icon field (e.g., `26. März 2026`)
3. Extract **time** from sidebar clock-icon field (e.g., `14:00 - 17:00 Uhr`)
4. Extract **location** from sidebar map-pin field
5. Extract **description** from main content area

### Date Parsing

**German months:**
`Januar, Februar, März, April, Mai, Juni, Juli, August, September, Oktober, November, Dezember`

**Formats to handle:**
- `17. März 2026` → `2026-03-17`
- `17.03.2026` → `2026-03-17`
- `17. - 20. März 2026` → start=17, end=20
- `17. März - 03. Juli 2026` → date range across months
- `01. Juli 2026 - 31. Juli 2026` → long multi-week range (e.g. examination period)
- `March 17, 2026 - March 20, 2026` → English date range

## Error Handling
- **HTTP errors:** Retry up to 3 times with exponential backoff (1s, 2s, 4s)
- **Parse errors:** Log warning, skip the event, continue with remaining events
- **Timeout:** 30 second timeout per request
- **Empty results:** Log warning but do not fail — produce an empty calendar
