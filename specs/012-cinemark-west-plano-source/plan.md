# Implementation Plan: Cinemark West Plano XD and ScreenX Showtime Ingestion Source

**Branch**: `012-cinemark-west-plano-source` | **Date**: 2026-07-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/012-cinemark-west-plano-source/spec.md`

## Summary

Add Cinemark West Plano XD and ScreenX (`https://www.cinemark.com/theatres/tx-plano/cinemark-west-plano-xd-and-screenx`,
`theaterId=231`) as a fourth showtime ingestion source, alongside Cinepolis McKinney, Texas
Theatre, and Angelika Film Center Dallas. The site's date-tab widget is backed by a first-party,
server-rendered Umbraco surface-controller endpoint
(`GET /umbraco/surface/Showtimes/GetByTheaterId?theaterId=231&showDate=YYYY-MM-DD`) — no client
JSON API reverse-engineering is required (unlike Angelika), but the feature adds one new wrinkle
not seen in any prior source: 70mm presentations appear as an entirely separate movie listing
(title suffixed `" 70mm"`, its own `CinemarkMovieId`) rather than a format tag on the base film's
listing, so the scraper must detect and normalize that title suffix into `format="70mm"` on the
underlying film. Other special formats (XD, ScreenX, D-BOX, RealD 3D) are conveyed via `<img
alt="...">` badges per showtime group and may co-occur. The feature adds a new
`scrape_cinemark_west_plano_showtimes()` function to `scraper.py`, a cinema-registration helper in
`storage.py`, a dispatch branch in `ingest.py`, and wiring into `main.py`'s cinema list — following
the exact structural precedent established by Texas Theatre (006) and Angelika Dallas (008).

## Technical Context

**Language/Version**: Python 3.11+ (existing project standard)

**Primary Dependencies**: `playwright` (+ `playwright-stealth`), reusing the existing
`_fetch_page_html_with_retry` / `REALISTIC_USER_AGENT` / `Stealth().apply_stealth_sync` fetch
pattern already used for Texas Theatre and Cinepolis; `BeautifulSoup` for HTML parsing (research.md §1)

**Storage**: SQLite via existing `cinema_recs.storage` module (`cinemas`, `showtimes`,
`ingestion_runs` tables) — no schema changes required

**Testing**: `pytest` (existing `tests/unit/` and `tests/integration/` suites)

**Target Platform**: Linux container (existing Docker image), Unraid host

**Project Type**: Single Python application (existing `src/cinema_recs/` package + `main.py` entrypoint)

**Performance Goals**: Single ingestion run completes within 30s (spec SC-005), matching existing sources — note this run walks ~75 per-date requests (research.md §4), so per-request latency and Playwright reuse across dates (one browser/context for the whole run, matching the Texas Theatre multi-month-walk pattern) is important to hit this budget

**Constraints**: Must not require new environment variables/config to be *mandatory* for existing
deployments (West Plano source URL and `theaterId=231` can be hardcoded as defaults, matching the
Texas Theatre/Angelika pattern in `config.py`)

**Scale/Scope**: Single additional venue/source; expected showtime volume is larger than the other
three sources combined (dozens of films × multiple formats × ~75 published dates)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Python-First**: PASS — new code is Python only, added to the existing `cinema_recs` package.
- **II. Docker-Native Deployment**: PASS — no new runtime dependencies beyond what's already in the Docker image (Playwright is already installed); no Dockerfile changes anticipated.
- **III. Unraid Runtime Compatibility**: PASS — no new required env vars; source URL/theater ID follow the existing hardcoded-default-with-optional-override convention.
- **IV. Simplicity & Solo-Maintainer Ergonomics**: PASS — reuses the existing `ScrapedShowtime`/`ScrapeResult`/`run_ingestion` abstractions exactly as Texas Theatre and Angelika did; no new abstraction layer, plugin system, or source-registry introduced. The 70mm-title-suffix normalization and multi-badge format join (research.md §2) are the only source-specific parsing logic, kept local to this source's parse function rather than generalized. The `ingest.py` dispatch remains the existing domain-substring `if/elif` chain.
- **V. Observability for Self-Hosting**: PASS — reuses existing `logger` calls and `IngestionRun` outcome/error_message recording; no silent failure paths introduced. Per-date fetch failures during the ~75-date walk are logged individually (matching Texas Theatre's per-page failure handling) rather than silently dropped.

No violations. Complexity Tracking section not needed.

## Project Structure

### Documentation (this feature)

```text
specs/012-cinemark-west-plano-source/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── contracts/            # Phase 1 output (/speckit-plan command)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/cinema_recs/
├── scraper.py     # + fetch_cinemark_west_plano_html(), extract_cinemark_west_plano_dates(),
│                  #   parse_cinemark_west_plano_html(), scrape_cinemark_west_plano_showtimes()
│                  #   (new, alongside existing Cinepolis/Texas Theatre/Angelika scrape functions)
├── config.py       # + CINEMARK_WEST_PLANO_NAME / _LOCATION / _DEFAULT_URL /
│                  #   _THEATER_ID constants (mirrors TEXAS_THEATRE_* / ANGELIKA_DALLAS_*)
├── storage.py       # + ensure_cinemark_west_plano_cinema() (mirrors ensure_angelika_dallas_cinema)
├── ingest.py         # + dispatch branch routing cinemark.com/theatres/tx-plano/... URLs (or
│                  #   source_type="cinemark_west_plano") to the new scrape function
└── models.py       # unchanged — reuses existing Cinema/Showtime/IngestionRun dataclasses

main.py             # + wire ensure_cinemark_west_plano_cinema() into bootstrap()'s cinemas list

tests/
├── unit/
│   └── test_cinemark_west_plano_scraper.py    # new — mirrors test_texas_theatre_scraper.py,
│                                                #   with dedicated cases for the 70mm-title-suffix
│                                                #   normalization and multi-badge format join
└── integration/
    └── test_cinemark_west_plano_ingestion.py  # new — mirrors test_angelika_dallas_ingestion.py
```

**Structure Decision**: Single-project layout (already established by the codebase). No new
top-level directories or modules — this feature extends the existing `scraper.py`, `config.py`,
`storage.py`, `ingest.py`, and `main.py` files in place, following the exact pattern the Texas
Theatre (006) and Angelika Dallas (008) sources established for adding another cinema source
without introducing a source-plugin abstraction.

## Complexity Tracking

*No violations — section not applicable.*
