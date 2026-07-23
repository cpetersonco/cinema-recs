# Implementation Plan: Showtime Recommendation Rules

**Branch**: `003-showtime-recommendation-rules` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-showtime-recommendation-rules/spec.md`

## Summary

Extend the existing cinema-recs pipeline (features 001/002) so that every
movie with a feature-002 TMDB match is resolved to its Letterboxd film
page (via `letterboxd.com/tmdb/{tmdb_id}/`), and evaluated against three
OR'd criteria — operator watchlist membership, Letterboxd rating above a
configured threshold, and membership on a fixed built-in best-of list —
to produce a recommendation status with matched reason(s) per movie.
Recommendation evaluation runs on the same periodic schedule as
ingestion/enrichment. The existing listing view is extended to visually
distinguish recommended showtimes and show why.

## Technical Context

**Language/Version**: Python 3.11+ (matches features 001/002)

**Primary Dependencies**: `requests` (already added by feature 002) —
Letterboxd's film/list/watchlist pages and the `/tmdb/{id}/` redirect all
responded `200`/`302` to a plain `requests` call in live testing, with no
Cloudflare bot-challenge and no custom headers needed (unlike feature
001's Cinepolis target). No HTML-parsing library is added — the three
data points needed (redirect target, JSON-LD `aggregateRating`, and
`data-target-link` poster-grid slugs) are extracted with stdlib
`re`/`json`. Reuses the existing `Flask`, `APScheduler`, and SQLite stack.

**Storage**: SQLite — same database file features 001/002 already use
(`cinema_recs.db`), extended with three new tables (`letterboxd_movie_data`,
`letterboxd_reference_list`, `movie_recommendation`)

**Testing**: `pytest` with `unittest.mock.patch` (stdlib), matching
feature 002's approach — no new test dependency

**Target Platform**: Same Linux Docker container as features 001/002,
deployed on the operator's Unraid server

**Project Type**: Single project — extends the existing
`src/cinema_recs/` package and container rather than introducing a new
service

**Performance Goals**: A recommendation evaluation pass (watchlist
re-fetch, up to one built-in best-of list re-fetch, and per-movie
Letterboxd lookups for any newly-matched movies) completes comfortably
within the existing hours-scale refresh interval, including deliberate
pacing between Letterboxd requests; this is not a request-latency-
sensitive path

**Constraints**: `LETTERBOXD_USERNAME` and `LETTERBOXD_RATING_THRESHOLD`
are both optional env vars; with neither set, evaluation must produce
zero recommendations without attempting any Letterboxd requests it
doesn't need (FR-005/SC-004). Requests to Letterboxd MUST be paced (fixed
delay), consistent with feature 002's TMDB pacing approach

**Scale/Scope**: One operator's watchlist (tens to low hundreds of
films, paginated) plus one built-in best-of list (250 films, paginated);
per-movie Letterboxd lookups bounded by the same "tens of distinct movies
per cycle" scale as feature 002's TMDB enrichment

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Python-First | All logic (Letterboxd client, recommendation evaluation, storage, view changes) implemented in Python | PASS |
| II. Docker-Native Deployment | Extends the existing single Docker image; no new container/service | PASS |
| III. Unraid Runtime Compatibility | New config via env vars only; no new volume/port requirements beyond features 001/002's existing ones | PASS |
| IV. Simplicity & Solo-Maintainer Ergonomics | Plain `requests`, no new HTML-parsing dependency, no dynamic config-reload mechanism (restart-on-env-change is sufficient per research.md), reuses the existing refresh-interval scheduler rather than adding a second interval knob | PASS |
| V. Observability for Self-Hosting | Failed Letterboxd fetches (watchlist/list/per-movie) are logged with the previous cached state preserved rather than silently emptied; recommendation outcomes logged per evaluation cycle | PASS |

No violations identified; Complexity Tracking is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/003-showtime-recommendation-rules/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── contracts/            # Phase 1 output (/speckit-plan command)
└── tasks.md               # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
└── cinema_recs/
    ├── config.py               # extend: add LETTERBOXD_USERNAME, LETTERBOXD_RATING_THRESHOLD env vars
    ├── models.py                # extend: LetterboxdMovieData, MovieRecommendation dataclasses
    ├── storage.py                 # extend: letterboxd_movie_data / letterboxd_reference_list / movie_recommendation tables + helpers
    ├── letterboxd_client.py         # new: paced Letterboxd fetch (tmdb->slug resolution, rating, watchlist/list slug scraping)
    ├── recommend.py                  # new: orchestrates fetch -> cache -> evaluate -> store, mirrors enrich.py
    ├── scheduler.py                   # extend: periodic job also runs enrichment + recommendation evaluation (closes feature 002's scheduler gap, needed for FR-002/FR-007)
    └── web.py                          # extend: listing view shows a recommended badge + reasons

main.py                                    # extend: run recommendation evaluation alongside the existing one-shot ingestion + enrichment calls

tests/
├── unit/
│   ├── test_letterboxd_client.py
│   └── test_recommend.py
└── integration/
    └── test_web_view.py                    # extend existing tests for recommended-badge display

requirements.txt                              # no changes (requests already present)
```

**Structure Decision**: This feature extends features 001/002's existing
single-project layout. `letterboxd_client.py` and `recommend.py` are new
files mirroring feature 002's `tmdb_client.py`/`enrich.py` split
(fetch/parse separated from orchestration), keeping the same
architectural pattern already established twice. No new Docker image,
container, or port is introduced. `scheduler.py` is extended (not just
`main.py`) because this feature is the first to have an explicit
periodic-re-evaluation requirement (FR-002/FR-007/SC-002) that a
one-shot-at-startup call can't satisfy alone.

## Complexity Tracking

*No violations — table intentionally omitted.*
