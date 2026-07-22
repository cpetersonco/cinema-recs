---

description: "Task list for Cinepolis McKinney Showtime Ingestion (Alpha Cinema)"

---

# Tasks: Cinepolis McKinney Showtime Ingestion (Alpha Cinema)

**Input**: Design documents from `/specs/001-cinepolis-showtime-ingestion/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/web-view.md, quickstart.md

**Tests**: Lightweight unit/integration tests are included per the plan's declared test structure (`tests/unit/`, `tests/integration/`) and the constitution's guidance to test logic with real failure risk (parsing, reconciliation). These are not a strict TDD gate — implement and test together within each story.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

Single project per plan.md: `src/cinema_recs/`, `tests/`, `main.py`, `Dockerfile` at repository root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project structure per plan.md (`src/cinema_recs/`, `tests/unit/`, `tests/integration/`) with `__init__.py` files
- [X] T002 Initialize Python project dependencies in `requirements.txt` (`playwright`, `beautifulsoup4`, `flask`, `apscheduler`, `pytest`)
- [X] T003 [P] Configure linting/formatting (e.g. `ruff`) in `pyproject.toml`
- [X] T004 [P] Create `Dockerfile` and `docker-compose.yml` per quickstart.md env vars (`CINEMA_RECS_SOURCE_URL`, `CINEMA_RECS_REFRESH_INTERVAL_HOURS`, `CINEMA_RECS_DATA_DIR`, `CINEMA_RECS_PORT`), including an entrypoint that honors `PUID`/`PGID` env vars (default to a non-root user, `chown` the data directory, then drop privileges) per constitution Principle III, and installing Playwright's Chromium browser + OS dependencies in the image

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Implement env-var configuration loader in `src/cinema_recs/config.py` (source URL, refresh interval, data dir, port)
- [X] T006 Implement SQLite schema and connection helper for `Cinema`, `Showtime`, `IngestionRun` tables (per data-model.md) in `src/cinema_recs/storage.py`
- [X] T007 [P] Create `Cinema`, `Showtime`, `IngestionRun` dataclasses (per data-model.md) in `src/cinema_recs/models.py`
- [X] T008 Implement startup logic that seeds/upserts the single Cinepolis McKinney `Cinema` row from config in `src/cinema_recs/storage.py` (depends on T006, T007)
- [X] T009 Configure structured logging to stdout in `src/cinema_recs/logging_setup.py`

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Capture current showtimes for the alpha cinema (Priority: P1) 🎯 MVP

**Goal**: Ingestion run scrapes Cinepolis McKinney's own website and stores showtimes, with no duplicates on repeated runs.

**Independent Test**: Run ingestion once and confirm showtimes (movie title, date, start time, format) are stored; run again against unchanged source data and confirm no duplicate records are created.

### Tests for User Story 1

- [X] T010 [P] [US1] Unit test for HTML parsing against fixture HTML (no browser launch) in `tests/unit/test_scraper.py`
- [X] T011 [P] [US1] Unit test for showtime upsert/uniqueness logic in `tests/unit/test_storage.py`

### Implementation for User Story 1

- [X] T012 [US1] Implement Cinepolis McKinney showtime fetch in `src/cinema_recs/scraper.py`: load `mckinney/showtimes` via stealth Playwright (needed to clear Cloudflare), then call Cinepolis' `/graphql` `showingsForDate` API in-page (with `site-id`/`circuit-id` headers) since the site is a JS SPA with no showtime markup in HTML; `fetch_showings_json()` and `parse_showings_response()` kept as separate functions. `format` is currently always `None` (API doesn't return it; see research.md)
- [X] T013 [US1] Implement showtime upsert logic keyed on `(cinema_id, movie_title, show_date, start_time, format)` in `src/cinema_recs/storage.py` (depends on T006, T007)
- [X] T014 [US1] Implement ingest orchestration (scrape → upsert → record `IngestionRun`) in `src/cinema_recs/ingest.py` (depends on T012, T013)
- [X] T015 [US1] Wire a one-shot ingestion entrypoint into `main.py` for manual validation (depends on T014)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently (quickstart.md steps 1 and 4)

---

## Phase 4: User Story 2 - Keep showtimes current as they change (Priority: P2)

**Goal**: Previously ingested showtimes are refreshed on a recurring schedule (every 2-4 hours), marking removed showtimes stale and picking up new ones.

**Independent Test**: Alter the set of showtimes available from the source between two ingestion runs and confirm stored data reflects additions and removals after the second run.

### Tests for User Story 2

- [X] T016 [P] [US2] Unit test for reconciliation logic (stale marking, reactivation of reappearing showtimes) in `tests/unit/test_ingest.py`

### Implementation for User Story 2

- [X] T017 [US2] Implement reconciliation in ingest orchestration: mark missing `active` showtimes `stale`, reactivate reappearing ones in `src/cinema_recs/ingest.py` (depends on T014) — implemented alongside T014
- [X] T018 [US2] Implement in-process recurring scheduler using configured refresh interval in `src/cinema_recs/scheduler.py` (depends on T014, T005)
- [X] T019 [US2] Wire scheduler startup into `main.py` alongside the one-shot entrypoint (depends on T018, T015)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - showtimes stay current automatically

---

## Phase 5: User Story 4 - View ingested showtimes (Priority: P2)

**Goal**: A minimal, human-readable listing view of currently active showtimes for the Cinepolis McKinney cinema.

**Independent Test**: Ingest a known set of showtimes and confirm the listing view displays each with correct movie title, date, start time, and format; confirm an empty state renders clearly when no showtimes exist yet.

### Tests for User Story 4

- [X] T020 [P] [US4] Integration test for `GET /` listing view, including the empty-data state, in `tests/integration/test_web_view.py`

### Implementation for User Story 4

- [X] T021 [US4] Implement Flask app with `GET /` listing active showtimes per contracts/web-view.md in `src/cinema_recs/web.py` (depends on T006, T007)
- [X] T022 [US4] Add empty-state handling ("no showtimes ingested yet") to the listing view in `src/cinema_recs/web.py` (depends on T021)
- [X] T023 [US4] Wire Flask app startup into `main.py` alongside the scheduler (depends on T021, T019)

**Checkpoint**: All user stories through P2 should now be independently functional - operator can view ingested showtimes in a browser

---

## Phase 6: User Story 3 - Verify ingestion health for the alpha cinema (Priority: P3)

**Goal**: Visibility into whether each ingestion run succeeded and how many showtimes it captured, with failures clearly distinguishable from zero-showtime successes.

**Independent Test**: Trigger an ingestion run and confirm a health view shows the run outcome and showtime count, including for a run where the source is unreachable.

### Tests for User Story 3

- [X] T024 [P] [US3] Integration test for `GET /health` view covering success, zero-showtime success, and failure outcomes in `tests/integration/test_web_view.py`

### Implementation for User Story 3

- [X] T025 [US3] Implement `GET /health` view rendering the latest `IngestionRun` outcome and showtime count per contracts/web-view.md in `src/cinema_recs/web.py` (depends on T006, T014, T021)
- [X] T026 [US3] Ensure ingest orchestration records `failure`/`partial` outcomes with `error_message` on scrape errors in `src/cinema_recs/ingest.py` (depends on T014) — implemented alongside T014

**Checkpoint**: All user stories should now be independently functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T027 [P] Write `README.md` with setup/run instructions referencing quickstart.md
- [X] T028 Add retry/error handling for transient scrape failures in `src/cinema_recs/scraper.py`
- [X] T029 [P] Add unit tests for the config loader in `tests/unit/test_config.py`
- [X] T030 Run full quickstart.md validation end-to-end against the live Cinepolis McKinney page — **DONE**: built and ran the real Docker image against `https://www.cinepolisusa.com/mckinney/showtimes`. First run: `outcome=success showtimes_captured=41`, correct movie titles and Central-time start times persisted to SQLite. Second run: still 41 active, zero duplicates (SC-002). `GET /` and `GET /health` both verified showing real data (SC-004, SC-006). Along the way, discovered and fixed: (1) default headless Playwright is also Cloudflare-blocked, not just plain HTTP — required `playwright-stealth` + realistic UA; (2) the site has no showtime HTML at all (Vue/Quasar SPA) — switched to calling its `/graphql` API in-page; (3) missing `tzdata` package in the container broke `ZoneInfo("America/Chicago")`. See research.md/plan.md for full writeup.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on Foundational completion; reconciliation/scheduler build directly on US1's ingest orchestration (T014)
- **User Story 4 (Phase 5)**: Depends on Foundational completion; storage/model reuse from Phase 2, independent of US2's scheduler logic
- **User Story 3 (Phase 6)**: Depends on Foundational and US1's ingest orchestration (T014); reuses US4's Flask app (T021)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories - the MVP
- **User Story 2 (P2)**: Builds on US1's ingest orchestration (T014) but is independently testable via manual re-runs
- **User Story 4 (P2)**: Independent of US2; only needs Foundational storage/models
- **User Story 3 (P3)**: Builds on US1's ingest orchestration (T014) and US4's Flask app (T021)

### Parallel Opportunities

- T003 and T004 (Setup) can run in parallel
- T007 (Foundational) can run in parallel with T005
- T010 and T011 (US1 tests) can run in parallel
- Once Foundational and US1 are done, US2 and US4 implementation can proceed in parallel (different files: `scheduler.py` vs `web.py`)

---

## Parallel Example: User Story 1

```bash
# Launch both User Story 1 tests together:
Task: "Unit test for HTML parsing in tests/unit/test_scraper.py"
Task: "Unit test for showtime upsert/uniqueness logic in tests/unit/test_storage.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run ingestion manually, confirm showtimes stored with no duplicates on re-run
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Validate independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Validate recurring refresh independently → Deploy/Demo
4. Add User Story 4 → Validate listing view independently → Deploy/Demo
5. Add User Story 3 → Validate health view independently → Deploy/Demo
6. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
