# Implementation Plan: AMC Stonebriar 24 Showtime Ingestion Source

**Branch**: `012-amc-stonebriar-source` | **Date**: 2026-07-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/012-amc-stonebriar-source/spec.md`

## Summary

Add AMC Stonebriar 24 (`https://www.amctheatres.com/movie-theatres/dallas-ft-worth/amc-stonebriar-24/showtimes`
— corrected from the singular `/showtime` given in the feature input, which 404s; see research.md
§1) as a fourth showtime ingestion source, alongside Cinepolis McKinney, Texas Theatre, and Angelika
Film Center Dallas. Live inspection (research.md §2) confirmed the site is a Next.js/RSC app
fronted by a Cloudflare-integrated Queue-It bot gate that blocks plain HTTP requests, so ingestion
requires Playwright + `playwright-stealth`, architecturally closest to the Angelika Dallas
integration (browser-driven fetch) but scraping the rendered DOM directly (no standalone JSON API
was observed), closer to Texas Theatre's DOM-parse approach. The feature adds a new
`scrape_amc_stonebriar_showtimes()` function to `scraper.py`, a corresponding cinema-registration
helper in `storage.py`, a dispatch entry in `ingest.py`'s explicit `source_type` map, and wiring
into `main.py`'s cinema list — following the exact structural precedent established by Texas
Theatre (006) and Angelika Dallas (008).

## Technical Context

**Language/Version**: Python 3.11+ (existing project standard)

**Primary Dependencies**: `playwright` (+ `playwright-stealth`) for browser-driven fetch and
DOM parsing (via `page.content()` + `BeautifulSoup`, matching Texas Theatre's approach); no new
dependencies

**Storage**: SQLite via existing `cinema_recs.storage` module (`cinemas`, `showtimes`,
`ingestion_runs` tables) — no schema changes required

**Testing**: `pytest` (existing `tests/unit/` and `tests/integration/` suites)

**Target Platform**: Linux container (existing Docker image), Unraid host

**Project Type**: Single Python application (existing `src/cinema_recs/` package + `main.py`
entrypoint)

**Performance Goals**: Single ingestion run completes within 30s (spec SC-004), matching existing
sources

**Constraints**: Must not require new environment variables/config to be *mandatory* for existing
deployments (AMC Stonebriar 24 source URL is hardcoded as a default in `config.py`, matching the
Texas Theatre/Angelika Dallas pattern, since this is a fixed additional venue rather than a
user-configurable primary source). Must extend `BLOCK_PAGE_MARKERS`/`looks_blocked()` (or an
equivalent redirect check) to detect this source's Queue-It gate (research.md §2), since the
existing markers only cover Cloudflare's own challenge-page text.

**Scale/Scope**: Single additional venue/source; AMC Stonebriar 24 is a 24-screen multiplex, so
expected showtime volume per run is materially higher than Cinepolis/Texas Theatre/Angelika
(dozens of titles x multiple formats x multiple showtimes/day x multi-day window)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Python-First**: PASS — new code is Python only, added to the existing `cinema_recs` package.
- **II. Docker-Native Deployment**: PASS — no new runtime dependencies beyond what's already in the
  Docker image (Playwright is already installed for Cinepolis/Texas Theatre/Angelika); no
  Dockerfile changes anticipated.
- **III. Unraid Runtime Compatibility**: PASS — no new required env vars; the source URL is a
  hardcoded default in `config.py`, same convention as Texas Theatre/Angelika Dallas.
- **IV. Simplicity & Solo-Maintainer Ergonomics**: PASS — reuses the existing
  `ScrapedShowtime`/`ScrapeResult`/`run_ingestion` abstractions exactly as prior sources did; no new
  abstraction layer, plugin system, or source-registry introduced. `ingest.py` dispatch remains the
  existing explicit dict (feature 011), extended with one more entry — not refactored further.
- **V. Observability for Self-Hosting**: PASS — reuses existing `logger` calls and `IngestionRun`
  outcome/error_message recording; no silent failure paths introduced.
- **VI. Explicit Over Inferred**: PASS — dispatch uses the explicit `source_type` map
  (`"amc_stonebriar"`), not domain-substring inference.
- **VII. Live-Verify External Integrations**: PASS — the source URL, site architecture (Next.js/RSC,
  no JSON API), anti-bot posture (Queue-It/Cloudflare gate), DOM shape (movie/format/showtime
  structure), and ticket URL pattern were all confirmed via live browser inspection in research.md,
  not assumed. One detail (exact multi-day date-walk mechanism, research.md §5) remains explicitly
  deferred to implementation-time live inspection rather than guessed here, consistent with how
  Texas Theatre's month-walk and Angelika's date-strip mechanisms were each confirmed against the
  live site before coding.
- **VIII. Network-Isolated Automated Tests**: PASS — unit tests will use captured/mocked HTML
  fixtures (matching `test_texas_theatre_scraper.py`/`test_angelika_dallas_scraper.py`); no live
  network calls in the test suite.
- **IX. Backward-Compatible Schema Migrations**: PASS — no schema changes; new `cinemas` row only.

No violations. Complexity Tracking section not needed.

## Project Structure

### Documentation (this feature)

```text
specs/012-amc-stonebriar-source/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── scraper_interface.md
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
src/cinema_recs/
├── models.py            # Existing dataclasses (Cinema, Showtime, IngestionRun) — unchanged
├── scraper.py            # Add scrape_amc_stonebriar_showtimes(), DOM parsing helpers, and
│                          # extend BLOCK_PAGE_MARKERS/looks_blocked() for the Queue-It gate
├── ingest.py              # Add "amc_stonebriar" entry to scrapers_by_source_type
├── storage.py             # Add ensure_amc_stonebriar_cinema()
└── config.py              # Add AMC_STONEBRIAR_NAME / _LOCATION / _DEFAULT_URL constants

main.py                    # bootstrap(): call ensure_amc_stonebriar_cinema(), append to cinemas list

tests/
├── unit/
│   └── test_amc_stonebriar_scraper.py       # DOM parsing & format extraction unit tests
└── integration/
    └── test_amc_stonebriar_ingestion.py     # Integration test with SQLite storage
```

**Structure Decision**: Single project layout consistent with existing `cinema_recs` package
structure under `src/cinema_recs/` and `tests/` — identical structure to the Texas Theatre (006)
and Angelika Dallas (008) onboardings.

## Complexity Tracking

*No constitution violations detected; table left blank.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
