# Implementation Plan: Full Showtime Window Ingestion

**Branch**: `009-full-showtime-window` | **Date**: 2026-07-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-full-showtime-window/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Each ingestion run currently only asks a source for a narrow slice of
its published calendar (Cinepolis: today only; Texas Theatre: whatever
calendar page it's pointed at, effectively one month; Angelika Dallas:
whatever a single API call returns). This means the feature-005 stale-
marking step — which flags any previously-active showtime not re-seen
in the current run — can wrongly mark real, still-published showings
stale and trigger false "cancelled"/"rescheduled" Discord alerts simply
because they fell outside that narrow window.

The fix is to make each source's scraper walk forward through its own
pagination (dates for Cinepolis, months for Texas Theatre; Angelika
Dallas's existing single call already appears to return a multi-date
window, pending live confirmation — research.md §3) until it reaches a
self-reported end of its published calendar, and to gate
`mark_stale_showtimes` on that full walk having completed successfully
— so a mid-walk failure is recorded as a failed/partial ingestion run
rather than silently treated as "nothing else is published."

## Technical Context

**Language/Version**: Python 3.11 (per `pyproject.toml`; existing project standard, Constitution I)

**Primary Dependencies**: Playwright (`playwright`, `playwright-stealth`) for Cinepolis/Texas Theatre/Angelika fetches (existing); `beautifulsoup4` for Texas Theatre HTML parsing (existing). No new dependencies introduced.

**Storage**: SQLite via the existing `src/cinema_recs/storage.py` module (existing `showtime` / `ingestion_run` tables; no schema migration — see data-model.md)

**Testing**: pytest (existing `tests/unit/` and `tests/integration/` suites; this feature extends `test_*_scraper.py` and `test_*_ingestion.py` for each of the three sources plus `ingest.py`'s stale-marking gate)

**Target Platform**: Linux server, Docker container on Unraid (existing deployment target, Constitution II/III) — unchanged by this feature

**Project Type**: Single Python application (existing `src/cinema_recs/` package) — unchanged

**Performance Goals**: No explicit new target; a full-window ingestion run for a given cinema completing within its existing scheduled refresh interval (`CINEMA_RECS_REFRESH_INTERVAL_HOURS`, default per feature 001) without overlapping the next scheduled run, given each source's observed published horizon is at most a few months (research.md §1/§2)

**Constraints**: No artificial cutoff on how far into the future showtimes may be captured (spec FR-006) — bounded only by each source's own published horizon, discovered by walking pagination to a self-reported end rather than a hardcoded date/month count

**Scale/Scope**: 3 existing sources, each single-cinema; per-run request volume grows from 1 request/source today to roughly "number of dates/months the source currently has published" (empirically observed: Texas Theatre ≈6-7 months forward from current, research.md §2; Cinepolis unconfirmed until implementation but expected to be on the order of days to a few weeks for a first-run multiplex chain)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Python-First**: PASS — all changes are within the existing `src/cinema_recs/` Python package (`scraper.py`, `ingest.py`); no second language introduced.
- **II. Docker-Native Deployment**: PASS — no new host dependencies, ports, or build steps; same `Dockerfile`/`docker run` invocation (quickstart.md).
- **III. Unraid Runtime Compatibility**: PASS — no new environment variables, volumes, or ports; existing config surface unchanged.
- **IV. Simplicity & Solo-Maintainer Ergonomics**: PASS — reuses the existing Playwright browser/page per run (research.md §1) rather than introducing new infrastructure (no queue, no separate crawler service). Angelika Dallas was originally assumed not to need pagination, but live verification during implementation showed otherwise (research.md §3); the resulting date-strip walk reuses the source's own already-computed date list rather than inventing a heuristic stop condition, keeping it no more complex than necessary. One deliberate complexity add — a "did the full-window walk complete" signal threaded through `ScrapeResult`/`run_ingestion` — is required to satisfy FR-003/FR-004 and is not speculative (see Complexity Tracking below for why a simpler alternative doesn't work).
- **V. Observability for Self-Hosting**: PASS — `IngestionRun.error_message` is required (data-model.md) to identify which page/date failed a mid-walk fetch, so a partial-window failure is diagnosable from container logs alone, consistent with existing failure logging in `ingest.py`.

No violations requiring the Complexity Tracking table's justification format beyond the one documented above (restated there for visibility).

## Project Structure

### Documentation (this feature)

```text
specs/009-full-showtime-window/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

No `contracts/` directory: this feature introduces no new external
interface (no new API endpoint, CLI flag, or webhook payload shape) —
it changes internal scraper/ingestion behavior only. The existing
Discord notification contract from feature 005 (`contracts/` under
`specs/005-showtime-cancellation-alerts/`) is reused unchanged.

### Source Code (repository root)

```text
src/cinema_recs/
├── scraper.py     # MODIFY: add per-source multi-page/date fetch loops
│                  #   (Cinepolis: loop dates via one shared browser
│                  #   context; Texas Theatre: follow "next month" links;
│                  #   Angelika Dallas: verify existing single call
│                  #   covers full window, per research.md §3) and a
│                  #   "walk completed fully" signal on ScrapeResult
├── ingest.py       # MODIFY: gate storage.mark_stale_showtimes on that
│                  #   signal; record failure/partial outcome with a
│                  #   descriptive error_message when a walk is incomplete
├── models.py       # UNCHANGED (no new fields; see data-model.md)
└── storage.py      # UNCHANGED (no schema migration; see data-model.md)

tests/
├── unit/
│   ├── test_scraper.py                    # MODIFY: Cinepolis date-loop + stop condition
│   ├── test_texas_theatre_scraper.py       # MODIFY: month-walk + stop condition
│   └── test_angelika_dallas_scraper.py     # MODIFY only if research.md §3's live
│                                            #   verification finds pagination is needed
└── integration/
    ├── test_ingestion.py (or per-source ingestion tests)  # MODIFY: assert
    │        mark_stale_showtimes is skipped on incomplete full-window fetch
    ├── test_texas_theatre_ingestion.py
    └── test_angelika_dallas_ingestion.py
```

**Structure Decision**: No new modules or packages — this is a
behavioral extension of the existing single-package `src/cinema_recs/`
layout (Constitution IV: no new project/service). All changes land in
the same three files (`scraper.py`, `ingest.py`, plus their existing
test counterparts) that prior source-onboarding and cancellation-alert
features already touched.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New "full-window walk completed" signal threaded through `ScrapeResult` → `run_ingestion` (rather than reusing today's plain success/exception control flow) | FR-003/FR-004 require distinguishing "fetched everything, genuinely nothing more is published" from "fetch died partway through a multi-page/date walk" — today's code only distinguishes "scrape raised" from "scrape returned," which collapses both of those into the same case once a scraper can partially succeed across many requests | Keeping today's plain success/exception distinction was rejected because it is exactly the bug this feature exists to fix: a scraper that fetches 5 of 7 months before failing would otherwise report those 5 months as a complete result, and `mark_stale_showtimes` would wrongly stale-mark real showings in the 2 unfetched months |
