# Implementation Plan: Consolidated Movie Listings with Ticket and Letterboxd Links

**Branch**: `010-consolidated-movie-listings` | **Date**: 2026-07-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-consolidated-movie-listings/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

`GET /`'s listing page currently renders one table row per active
`Showtime` record, so a movie with many active showtimes at one venue
(now the normal case since feature 009 fetches each source's full
published calendar) appears as a wall of near-duplicate rows. This
feature groups each venue section's showtimes by movie title in
`web.py`, keeping only each movie's earliest upcoming active showtime as
that movie's single row (reusing the same "earliest active showtime"
semantics `storage.get_next_showtime_for_movie` already applies
elsewhere), and adds two new pieces of information to that row: a link
to the representative showtime's ticket-purchase page (`Showtime.ticket_url`,
already captured, just not previously shown), and the movie's Letterboxd
rating rendered as a link to its Letterboxd film page (`LetterboxdMovieData`,
already fetched by the recommendation cycle, just not previously shown).
No new data is captured, no schema changes, no new dependencies —
`web.py`'s `listing()` view and `LISTING_TEMPLATE` are the only things
that change.

## Technical Context

**Language/Version**: Python 3.11 (per `pyproject.toml`; existing project standard, Constitution I)

**Primary Dependencies**: Flask (`render_template_string`, existing) — no new dependencies introduced

**Storage**: SQLite via the existing `src/cinema_recs/storage.py` module; no schema migration (data-model.md) — reuses `list_active_showtimes`, `get_movie_metadata`, `get_movie_recommendation`, and (newly read by `web.py`) `get_letterboxd_movie_data`

**Testing**: pytest (existing `tests/integration/test_web_view.py`; this feature extends it with consolidation/ticket-link/Letterboxd-link cases)

**Target Platform**: Linux server, Docker container on Unraid (existing deployment target, Constitution II/III) — unchanged by this feature

**Project Type**: Single Python application (existing `src/cinema_recs/` package) — unchanged

**Performance Goals**: No explicit new target; grouping happens in Python over data already fetched in one query per cinema (research.md §1), so page load time is not meaningfully affected

**Constraints**: Presentation-layer only (spec FR-008) — no change to what's ingested, stored, or how ingestion/recommendation/notification pipelines behave

**Scale/Scope**: Same 3 existing cinemas; per-request work changes from "render N showtime rows" to "group N showtimes into M movie rows, M ≤ N" within a single already-fetched list per cinema — no new queries per movie (research.md §1)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Python-First**: PASS — all changes are within the existing `src/cinema_recs/web.py`; no second language introduced.
- **II. Docker-Native Deployment**: PASS — no new host dependencies, ports, or build steps; same `Dockerfile`/`docker run` invocation (quickstart.md).
- **III. Unraid Runtime Compatibility**: PASS — no new environment variables, volumes, or ports; existing config surface unchanged.
- **IV. Simplicity & Solo-Maintainer Ergonomics**: PASS — grouping is done in Python over an already-fetched, already-ordered list rather than adding new SQL/queries or a new storage abstraction (research.md §1); reuses existing `Showtime.ticket_url` and `LetterboxdMovieData` fields/tables rather than introducing new data capture (research.md §2/§3).
- **V. Observability for Self-Hosting**: PASS — no new failure modes are introduced (grouping over already-validated data, both new fields already nullable/handled elsewhere in the app); no new logging needed since nothing here can newly fail in a way that needs a log line beyond what already exists.

No violations requiring the Complexity Tracking table.

## Project Structure

### Documentation (this feature)

```text
specs/010-consolidated-movie-listings/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── web-view.md      # Phase 1 output (/speckit-plan command) — updates feature 001's GET / contract
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/cinema_recs/
├── web.py          # MODIFY: group each cinema section's showtimes by
│                   #   movie_title (keeping the earliest per group),
│                   #   read get_letterboxd_movie_data per distinct
│                   #   movie, and update LISTING_TEMPLATE to render one
│                   #   row per movie with a ticket link and a
│                   #   Letterboxd-linked rating
├── storage.py       # UNCHANGED (no schema migration; get_letterboxd_movie_data already exists)
└── models.py         # UNCHANGED

tests/
└── integration/
    └── test_web_view.py   # MODIFY: add consolidation, ticket-link, and
                           #   Letterboxd-rating-link test cases
```

**Structure Decision**: No new modules — this is a behavioral change
confined to the existing `src/cinema_recs/web.py` view and its template
string, plus its existing integration test file. No new project/service
(Constitution IV).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations — table intentionally omitted.
