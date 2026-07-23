# Implementation Plan: Angelika Film Center Dallas Showtime Ingestion Source

**Branch**: `008-angelika-dallas-source` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/008-angelika-dallas-source/spec.md`

## Summary

Add Angelika Film Center Dallas (`https://angelikafilmcenter.com/dallas`) as a third showtime ingestion source, alongside the existing Cinepolis McKinney and Texas Theatre sources. The site is a React single-page app operated by Reading Cinemas' shared multi-brand booking platform, backed by a JSON API at `production-api.readingcinemas.com` — architecturally closer to the Cinepolis GraphQL-API integration than to the Texas Theatre static-HTML integration. The feature adds a new `scrape_angelika_dallas_showtimes()` function to the existing `scraper.py` module, a corresponding cinema-registration helper in `storage.py`, a dispatch branch in `ingest.py`, and wiring into `main.py`'s cinema list — following the exact structural precedent already established by the Texas Theatre onboarding (spec 006).

## Technical Context

**Language/Version**: Python 3.11+ (existing project standard)

**Primary Dependencies**: `playwright` (+ `playwright-stealth`) for API/network fetch, `httpx` or Playwright's own request context for the JSON API call — final choice made during implementation once the exact API auth/headers are confirmed (see research.md §1)

**Storage**: SQLite via existing `cinema_recs.storage` module (`cinemas`, `showtimes`, `ingestion_runs` tables) — no schema changes required

**Testing**: `pytest` (existing `tests/unit/` and `tests/integration/` suites)

**Target Platform**: Linux container (existing Docker image), Unraid host

**Project Type**: Single Python application (existing `src/cinema_recs/` package + `main.py` entrypoint)

**Performance Goals**: Single ingestion run completes within 30s (spec SC-004), matching existing sources

**Constraints**: Must not require new environment variables/config to be *mandatory* for existing deployments (Angelika Dallas source URL can be hardcoded as a default, matching the Texas Theatre pattern in `config.py`, since this is a fixed additional venue rather than a user-configurable primary source)

**Scale/Scope**: Single additional venue/source; expected showtime volume is comparable to Cinepolis McKinney (dozens of showtimes per ingestion run)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Python-First**: PASS — new code is Python only, added to the existing `cinema_recs` package.
- **II. Docker-Native Deployment**: PASS — no new runtime dependencies beyond what's already in the Docker image (Playwright is already installed for Cinepolis/Texas Theatre); no Dockerfile changes anticipated.
- **III. Unraid Runtime Compatibility**: PASS — no new required env vars; if an override URL is exposed it follows the existing `CINEMA_RECS_SOURCE_URL`-style optional env var convention, not a mandatory one.
- **IV. Simplicity & Solo-Maintainer Ergonomics**: PASS — reuses the existing `ScrapedShowtime`/`ScrapeResult`/`run_ingestion` abstractions exactly as Texas Theatre did; no new abstraction layer, plugin system, or source-registry introduced. The `ingest.py` dispatch remains a simple domain-substring `if/elif` chain, consistent with current code (not refactored into a registry as part of this feature, to avoid unrelated scope creep).
- **V. Observability for Self-Hosting**: PASS — reuses existing `logger` calls and `IngestionRun` outcome/error_message recording; no silent failure paths introduced.

No violations. Complexity Tracking section not needed.

## Project Structure

### Documentation (this feature)

```text
specs/008-angelika-dallas-source/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/cinema_recs/
├── scraper.py     # + fetch_angelika_dallas_sessions(), parse_angelika_dallas_sessions(),
│                   #   scrape_angelika_dallas_showtimes() (new, alongside existing
│                   #   Cinepolis and Texas Theatre scrape functions)
├── config.py       # + ANGELIKA_DALLAS_NAME / _LOCATION / _DEFAULT_URL constants
│                   #   (mirrors TEXAS_THEATRE_* constants)
├── storage.py       # + ensure_angelika_dallas_cinema() (mirrors ensure_texas_theatre_cinema)
├── ingest.py         # + dispatch branch routing angelikafilmcenter.com URLs to the
│                   #   new scrape function
└── models.py       # unchanged — reuses existing Cinema/Showtime/IngestionRun dataclasses

main.py             # + wire ensure_angelika_dallas_cinema() into bootstrap()'s cinemas list

tests/
├── unit/
│   └── test_angelika_dallas_scraper.py    # new — mirrors test_texas_theatre_scraper.py
└── integration/
    └── test_angelika_dallas_ingestion.py  # new — mirrors test_texas_theatre_ingestion.py
```

**Structure Decision**: Single-project layout (already established by the codebase). No new top-level directories or modules — this feature extends the existing `scraper.py`, `config.py`, `storage.py`, `ingest.py`, and `main.py` files in place, following the exact pattern the Texas Theatre source (spec 006) established for adding a second/third cinema source without introducing a source-plugin abstraction.

## Complexity Tracking

*No violations — section not applicable.*
