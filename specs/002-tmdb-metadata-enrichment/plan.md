# Implementation Plan: Movie Metadata Enrichment via TMDB

**Branch**: `002-tmdb-metadata-enrichment` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-tmdb-metadata-enrichment/spec.md`

## Summary

Extend the existing cinema-recs pipeline (feature 001) so that every
distinct movie title captured by showtime ingestion is looked up against
TMDB's public REST API, caching genre/overview/release year/rating/
runtime/poster per movie and recording a TMDB identifier. That
identifier is also exposed as a stable "translation surface" so feature
003 can later resolve each movie's corresponding Letterboxd entry via
`letterboxd.com/tmdb/{tmdb_id}/` rather than re-matching the raw scraped
title. The existing listing view is extended to show genre/rating/
poster inline, and enrichment failures are logged the same way ingestion
failures already are.

## Technical Context

**Language/Version**: Python 3.11+ (matches feature 001)

**Primary Dependencies**: `requests` (TMDB is a normal, non-bot-protected
public REST API, so no headless browser is needed here — unlike feature
001's Cinepolis scraper); reuses feature 001's existing `Flask`,
`APScheduler`, and SQLite stack. `BeautifulSoup4` is not needed (TMDB
returns JSON, not HTML).

**Storage**: SQLite — same database file feature 001 already created
(`cinema_recs.db`), extended with two new tables (`movie_metadata`,
`enrichment_attempt`)

**Testing**: `pytest` with `unittest.mock.patch` (standard library) to
mock TMDB HTTP calls in unit tests — no new mocking dependency needed
(unlike feature 001, which needed `responses` before dropping HTTP calls
from the scraper entirely in favor of in-page `fetch()`)

**Target Platform**: Same Linux Docker container as feature 001, deployed
on the operator's Unraid server

**Project Type**: Single project — extends the existing
`src/cinema_recs/` package and container rather than introducing a new
service

**Performance Goals**: An enrichment pass over a batch of newly observed
movies (typically single digits to low tens per ingestion cycle)
completes in well under the existing ~30s ingestion budget, including
deliberate pacing between TMDB requests

**Constraints**: A TMDB API key MUST be supplied via environment
variable, consistent with feature 001's config pattern; TMDB requests
MUST be paced (a small fixed delay between sequential calls) rather than
fired in a burst, to stay comfortably under TMDB's rate limits without
needing a more complex rate-limiting algorithm

**Scale/Scope**: One cinema's worth of distinct movie titles at a time
(tens, not hundreds, of distinct movies active at once) — each looked up
and cached at most once

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Python-First | All logic (TMDB client, matching, storage, view changes) implemented in Python | PASS |
| II. Docker-Native Deployment | Extends the existing single Docker image; no new container/service | PASS |
| III. Unraid Runtime Compatibility | TMDB API key via env var; no new volume/port requirements beyond feature 001's existing ones | PASS |
| IV. Simplicity & Solo-Maintainer Ergonomics | Plain `requests` (no browser needed here); simple fixed-delay pacing instead of a token-bucket rate limiter; stdlib `unittest.mock` instead of a new test dependency; naive title-similarity matching (see research.md) instead of a fuzzy-matching library | PASS |
| V. Observability for Self-Hosting | Enrichment Attempt records mirror the existing Ingestion Run observability pattern (FR-008); failures logged to stdout | PASS |

No violations identified; Complexity Tracking is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/002-tmdb-metadata-enrichment/
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
    ├── config.py          # extend: add TMDB_API_KEY env var
    ├── models.py           # extend: MovieMetadata, EnrichmentAttempt dataclasses
    ├── storage.py           # extend: movie_metadata / enrichment_attempt tables + helpers
    ├── tmdb_client.py        # new: paced TMDB search + detail fetch, matching logic
    ├── enrich.py              # new: orchestrates lookup -> match -> store, mirrors ingest.py
    └── web.py                  # extend: listing view shows genre/rating/poster

main.py                          # extend: run enrichment alongside ingestion

tests/
├── unit/
│   ├── test_tmdb_client.py
│   └── test_enrich.py
└── integration/
    └── test_web_view.py          # extend existing tests for enriched fields

requirements.txt                   # extend: add `requests`
```

**Structure Decision**: This feature extends feature 001's existing
single-project layout rather than introducing a new module boundary or
service. `tmdb_client.py` and `enrich.py` are new files mirroring the
existing `scraper.py`/`ingest.py` split (fetch/parse separated from
orchestration), keeping the same architectural pattern already
established. No new Docker image, container, or port is introduced.

## Complexity Tracking

*No violations — table intentionally omitted.*
