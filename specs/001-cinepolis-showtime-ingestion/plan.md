# Implementation Plan: Cinepolis McKinney Showtime Ingestion (Alpha Cinema)

**Branch**: `001-cinepolis-showtime-ingestion` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-cinepolis-showtime-ingestion/spec.md`

## Summary

Build a small Python service that periodically pulls showtimes for the
Cinepolis McKinney location from Cinepolis' own GraphQL API (loaded via a
stealth-Playwright browser session, since the site is Cloudflare-protected
and its showtime data only exists behind that API — not in server-rendered
HTML), reconciles them against previously stored showtimes (adding new
ones, removing stale ones, avoiding duplicates), and exposes a minimal
listing view plus ingestion-run health so the pipeline can be trusted
before more cinemas are added. The whole feature runs as a single Docker
container suitable for Unraid, storing data in SQLite on a mounted volume.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `Playwright` + `playwright-stealth` (headless
Chromium with stealth evasions and a realistic user-agent — needed
because Cinepolis' site is behind Cloudflare bot protection that blocks
both plain HTTP requests and default headless Chromium), `APScheduler`
(in-process recurring job every 2-4 hours), `Flask` + Jinja2 (minimal
listing view and health output). `BeautifulSoup4` is no longer a
dependency — see research.md; Cinepolis' showtimes come from a GraphQL
API (`/graphql`) called via an in-page `fetch()`, not HTML parsing.

**Storage**: SQLite (single file on a mounted Docker volume)

**Testing**: `pytest` with fetch/parse separated so `test_scraper.py` can
unit-test JSON-response parsing against small fixtures without launching
a browser

**Target Platform**: Linux Docker container, deployed on an Unraid server

**Project Type**: Single project (one Python service combining scraper,
scheduler, storage, and a minimal web view)

**Performance Goals**: An ingestion run against a single cinema's page
completes in under 30 seconds; the listing view renders in under 1 second
for the expected showtime volume (dozens to low hundreds of rows)

**Constraints**: Must build and run as a single Docker image; all runtime
configuration (scrape target URL, refresh interval, listen port, data
directory) via environment variables; persistent data MUST live under a
path meant for a mounted volume, not baked into the image

**Scale/Scope**: One cinema (Cinepolis McKinney) for this phase; on the
order of tens to a couple hundred showtimes active at any time

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Python-First | All logic (scraping, storage, scheduling, view) implemented in Python | PASS |
| II. Docker-Native Deployment | Feature ships as one buildable Docker image; no host-only setup steps | PASS |
| III. Unraid Runtime Compatibility | Config via env vars; SQLite file under a mountable data directory; configurable listen port; container entrypoint honors `PUID`/`PGID` env vars rather than assuming a fixed host UID/GID | PASS |
| IV. Simplicity & Solo-Maintainer Ergonomics | Single process, single dependency-light web framework, SQLite instead of a separate DB service, in-process scheduler instead of external cron/service. Playwright + stealth is a heavier dependency than originally planned, and calling Cinepolis' own GraphQL API (found via network inspection) instead of a documented interface adds fragility (see Complexity Tracking), but both are the minimal viable mechanism confirmed to actually retrieve real data | PASS (justified) |
| V. Observability for Self-Hosting | Ingestion run outcome (success/failure, count) logged to stdout per FR-009; scraping/reconciliation errors logged with context | PASS |

One justified complexity deviation (Playwright); see Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/001-cinepolis-showtime-ingestion/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
└── cinema_recs/
    ├── __init__.py
    ├── config.py         # env-var driven configuration
    ├── models.py         # Cinema, Showtime, IngestionRun dataclasses
    ├── storage.py         # SQLite schema + read/write/reconcile helpers
    ├── scraper.py         # Cinepolis McKinney GraphQL fetch + parse
    ├── ingest.py           # orchestrates scrape -> reconcile -> record run
    ├── scheduler.py        # recurring ingestion trigger (every 2-4h)
    └── web.py              # Flask app: listing view + run-health view

main.py                      # entrypoint: starts scheduler + web server

tests/
├── unit/
│   ├── test_scraper.py
│   ├── test_storage.py
│   └── test_ingest.py
└── integration/
    └── test_ingestion_cycle.py

Dockerfile
docker-compose.yml
requirements.txt
```

**Structure Decision**: Single Python project (`src/cinema_recs/`) packaged
as one Docker image. No frontend/backend split and no multi-service
architecture — the listing view is served by the same Flask process that
also runs the scheduler, consistent with the Simplicity principle. Data
persists to a SQLite file expected to live under a mounted volume (e.g.
`/data/cinema_recs.db`), keeping state out of the image per the
Unraid Runtime Compatibility principle.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Playwright + `playwright-stealth` (headless Chromium with evasions) instead of plain `requests` | Confirmed directly against the live site: plain `requests` AND default headless Playwright both get a Cloudflare block page; stealth evasions + a realistic user-agent were required to get real content | Plain `requests` and default headless Playwright were both tried against the live site and returned an HTTP block/interstitial, not showtime data — not viable regardless of added complexity |
| Calling Cinepolis' undocumented GraphQL API (with hardcoded `site-id`/`circuit-id` headers for McKinney) instead of parsing HTML | Confirmed the site is a Vue/Quasar SPA with no showtime markup in server-rendered HTML at all — the data only exists via this API at runtime, so there is no DOM to scrape | DOM scraping was the original plan but is not viable — there is nothing in the HTML to select; the API is the only real source of the data. Risk accepted: this is an undocumented internal API that could change without notice, unlike a public/versioned API |
