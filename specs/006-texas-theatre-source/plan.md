# Implementation Plan: Texas Theatre Showtime Source Ingestion

**Branch**: `006-texas-theatre-source` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-texas-theatre-source/spec.md`

## Summary

Implement showtime ingestion for Texas Theatre (`https://thetexastheatre.com/calendar`) in `cinema_recs`. This includes fetching calendar event markup using Playwright stealth contexts, extracting movie titles, dates, start times, projection formats (e.g. 35mm, 70mm, 16mm, Digital), and ticketing links, and persisting showtime records idempotently to SQLite storage via `ingest.py`.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Playwright (`playwright.sync_api`), `playwright-stealth`, standard library (`datetime`, `re`, `logging`, `zoneinfo`)

**Storage**: SQLite database (`cinema.db`) via `cinema_recs.storage`

**Testing**: `pytest` (unit tests with mock HTML calendar payloads, integration tests against storage)

**Target Platform**: Docker container running on Unraid server

**Project Type**: Python CLI & background ingestion service

**Performance Goals**: Complete single calendar ingestion run within 30 seconds

**Constraints**: Python-first, containerized runtime, stdout/stderr logging, zero duplicate records

**Scale/Scope**: ~30-100 calendar screenings per month for Texas Theatre

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Python-First**: All new scraper and ingestion code is written strictly in Python.
- [x] **II. Docker-Native Deployment**: Scraper runs inside existing Docker environment with Playwright browser support.
- [x] **III. Unraid Runtime Compatibility**: Uses existing SQLite database volume mount and environment variables.
- [x] **IV. Simplicity & Solo-Maintainer Ergonomics**: Extends existing `scraper.py` and `ingest.py` modules without introducing complex abstractions or additional databases.
- [x] **V. Observability for Self-Hosting**: Emits clear log messages to stdout/stderr for run progress, warning for skipped entries, and error details on failure.

## Project Structure

### Documentation (this feature)

```text
specs/006-texas-theatre-source/
├── spec.md              # Feature specification
├── plan.md              # This implementation plan
├── research.md          # Phase 0 research findings
├── data-model.md        # Phase 1 data model schema
├── quickstart.md        # Phase 1 validation guide
├── contracts/           # Phase 1 interface contracts
│   └── scraper_interface.md
└── checklists/
    └── requirements.md
```

### Source Code Layout

```text
src/cinema_recs/
├── models.py            # Existing dataclasses (Cinema, Showtime, IngestionRun)
├── scraper.py           # Add scrape_texas_theatre_showtimes() & format regex extraction
├── ingest.py            # Add Texas Theatre routing in run_ingestion()
├── storage.py           # Ensure Texas Theatre cinema record helper
└── config.py            # Configuration defaults

tests/
├── unit/
│   └── test_texas_theatre_scraper.py  # Unit tests for HTML calendar parsing & format extraction
└── integration/
    └── test_texas_theatre_ingestion.py # Integration test with SQLite storage
```

**Structure Decision**: Single project layout consistent with existing `cinema_recs` package structure under `src/cinema_recs/` and `tests/`.

## Complexity Tracking

*No constitution violations detected; table left blank.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
