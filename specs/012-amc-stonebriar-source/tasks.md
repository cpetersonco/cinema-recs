# Tasks: AMC Stonebriar 24 Showtime Ingestion Source

**Input**: Design documents from `/specs/012-amc-stonebriar-source/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/scraper_interface.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Venue configuration constants and database registration helper

- [X] T001 Define `AMC_STONEBRIAR_NAME`, `AMC_STONEBRIAR_LOCATION`, `AMC_STONEBRIAR_DEFAULT_URL` (the corrected plural `/showtimes` URL, research.md §1) constants in `src/cinema_recs/config.py` (mirrors existing `ANGELIKA_DALLAS_*` constants)
- [X] T002 [P] Add `ensure_amc_stonebriar_cinema(db_path)` cinema record helper/seeder with `source_type="amc_stonebriar"` in `src/cinema_recs/storage.py` (mirrors `ensure_angelika_dallas_cinema`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Scraper function stub, bot-gate detection, ingestion routing, and application wiring

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Inspect live network traffic against `https://www.amctheatres.com/movie-theatres/dallas-ft-worth/amc-stonebriar-24/showtimes` (Playwright-driven browser) to confirm: (a) the exact markup/attribute each showtime button uses to expose its numeric session id (needed to build `ticket_url` without clicking every button, research.md §4), and (b) the real request/URL scheme the "Today" date-picker uses to load additional days (research.md §5, left unresolved during planning); record findings as code comments in `src/cinema_recs/scraper.py` (same documentation style as the existing Cinepolis `MCKINNEY_SITE_ID`/`CINEPOLIS_CIRCUIT_ID` header comment)
- [X] T004 Extend `BLOCK_PAGE_MARKERS`/`looks_blocked()` (or add an equivalent redirect-URL check) in `src/cinema_recs/scraper.py` to detect the `queue.amctheatres.com` Queue-It/Cloudflare gate confirmed in research.md §2, raising `BlockedError` consistently with other sources
- [X] T005 Implement `scrape_amc_stonebriar_showtimes()` scraper function stub (signature per `contracts/scraper_interface.md`) in `src/cinema_recs/scraper.py`
- [X] T006 Register `"amc_stonebriar": scrape_amc_stonebriar_showtimes` in the `scrapers_by_source_type` dispatch map in `run_ingestion()` in `src/cinema_recs/ingest.py`
- [X] T007 Wire `ensure_amc_stonebriar_cinema()` into `bootstrap()`'s `cinemas` list in `main.py`, alongside the existing Cinepolis, Texas Theatre, and Angelika Dallas cinemas, so ingestion/enrichment/notifications/scheduler/web view all pick up the new source

**Checkpoint**: Foundational scraper routing, bot-gate detection, and app wiring established.

---

## Phase 3: User Story 1 - Ingest upcoming showtimes from AMC Stonebriar 24 (Priority: P1) 🎯 MVP

**Goal**: Load the AMC Stonebriar 24 showtimes page via Playwright, parse film titles/dates/start times from the rendered DOM, and store showtime records idempotently in SQLite.

**Independent Test**: Trigger ingestion for the AMC Stonebriar 24 source and verify showtimes are stored in `cinema.db` per `quickstart.md` Scenario 1.

### Tests for User Story 1

- [X] T008 [P] [US1] Unit test for AMC Stonebriar 24 DOM fetching & date/time parsing (using a captured/mocked HTML fixture, per constitution VIII) in `tests/unit/test_amc_stonebriar_scraper.py`
- [X] T009 [P] [US1] Integration test for AMC Stonebriar 24 showtime ingestion run in `tests/integration/test_amc_stonebriar_ingestion.py`

### Implementation for User Story 1

- [X] T010 [US1] Implement `_fetch_amc_stonebriar_page_html_with_retry()` Playwright-driven page load (stealth context, retry/backoff, `BlockedError` handling via T004) in `src/cinema_recs/scraper.py`
- [X] T011 [US1] Implement `parse_amc_stonebriar_html()` to map the rendered showtimes DOM (movie card → format section → showtime buttons, research.md §3) into `ScrapedShowtime` records (title, show_date, start_time in `CENTRAL_TIME`) in `src/cinema_recs/scraper.py`
- [X] T012 [US1] Complete `scrape_amc_stonebriar_showtimes()` to call fetch + parse and return `ScrapeResult` (`reported_count` reflecting skipped entries) in `src/cinema_recs/scraper.py`

**Checkpoint**: At this point, User Story 1 is fully functional and testable independently (MVP ready).

---

## Phase 4: User Story 2 - Capture screening formats, auditorium, and ticket links (Priority: P2)

**Goal**: Extract presentation format (e.g. LASER AT AMC, IMAX WITH LASER AT AMC, Dolby Cinema, RealD 3D) and direct ticket purchase links into showtime records.

**Independent Test**: Ingest a listing with a non-default format (e.g. IMAX) and verify the stored record's `format` and `ticket_url` match the source, per `quickstart.md` Scenario 2.

### Tests for User Story 2

- [X] T013 [P] [US2] Unit test for presentation format-section extraction and ticket URL parsing in `tests/unit/test_amc_stonebriar_scraper.py`

### Implementation for User Story 2

- [X] T014 [US2] Implement presentation format extraction from each format-section header (e.g. `"LASER AT AMC"`, `"IMAX WITH LASER AT AMC"`) in `parse_amc_stonebriar_html()` in `src/cinema_recs/scraper.py`
- [X] T015 [US2] Implement `ticket_url` construction (`https://www.amctheatres.com/showtimes/{session_id}/seats`, research.md §4) from the per-showtime session id identified in T003, in `parse_amc_stonebriar_html()` in `src/cinema_recs/scraper.py`

**Checkpoint**: User Story 2 features (format and ticket link capture) complete and independently testable.

---

## Phase 5: User Story 3 - Synchronize schedule updates and cancellations (Priority: P3)

**Goal**: Refresh existing AMC Stonebriar 24 showtimes on each ingestion run across the venue's full published date range, update modified event details, and mark removed showtimes as stale.

**Independent Test**: Re-run ingestion after a simulated schedule change and verify stored records accurately reflect additions/removals/updates, per `quickstart.md` Scenario 3.

### Tests for User Story 3

- [X] T016 [P] [US3] Unit test for the multi-day walk logic (using the date-navigation mechanism confirmed in T003), including the `MAX_CONSECUTIVE_EMPTY_PERIODS` stop condition, in `tests/unit/test_amc_stonebriar_scraper.py`
- [X] T017 [P] [US3] Integration test for stale showtime reconciliation and repeated-run idempotency in `tests/integration/test_amc_stonebriar_ingestion.py`

### Implementation for User Story 3

- [X] T018 [US3] Implement the multi-day walk (across the venue's full published date range using the mechanism confirmed in T003) with per-day retry and early-stop-on-failure, returning `complete`/`incomplete_reason` per `contracts/scraper_interface.md`, in `scrape_amc_stonebriar_showtimes()` in `src/cinema_recs/scraper.py`
- [X] T019 [US3] Verify stale showtime marking (`storage.mark_stale_showtimes`) and partial/failure `IngestionRun` outcome reporting behave correctly for AMC Stonebriar 24 fetch errors/partial parses in `src/cinema_recs/ingest.py` and `src/cinema_recs/scraper.py`

**Checkpoint**: All user stories complete and functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final logging, documentation verification, and validation scenarios

- [X] T020 [P] Add structured logging for AMC Stonebriar 24 ingestion progress, fetch errors, and bot-gate/block detection in `src/cinema_recs/scraper.py`
- [X] T021 Execute end-to-end validation scenarios documented in `specs/012-amc-stonebriar-source/quickstart.md`
- [X] T022 Run `graphify update .` to refresh the knowledge graph with the new scraper/storage/ingest/config/main.py changes (per project CLAUDE.md graphify rules)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories.
- **User Stories (Phase 3+)**: All depend on Foundational phase completion.
  - US1 (P1) -> US2 (P2) -> US3 (P3)
- **Polish (Phase 6)**: Depends on completion of user stories.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational phase (Phase 2).
- **User Story 2 (P2)**: Extends US1 DOM-parsing logic (`parse_amc_stonebriar_html()`).
- **User Story 3 (P3)**: Extends US1 fetch/walk logic and ingestion storage lifecycle.

### Parallel Opportunities

- T001 and T002 (Phase 1) can run in parallel (different files).
- T008 and T009 (US1 tests) can run in parallel (different test files).
- T013 (US2 test), T016 and T017 (US3 tests) can each run in parallel with sibling tests in the same phase (different concerns/files).
- T020 (Polish logging) can run in parallel with T021 (manual validation) once all stories are complete.

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for AMC Stonebriar 24 DOM fetching & date/time parsing in tests/unit/test_amc_stonebriar_scraper.py"
Task: "Integration test for AMC Stonebriar 24 showtime ingestion run in tests/integration/test_amc_stonebriar_ingestion.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational) — including the live DOM/date-mechanism inspection task (T003), which is a hard prerequisite for any real parsing work.
2. Complete Phase 3 (User Story 1).
3. Validate User Story 1 using `tests/unit/test_amc_stonebriar_scraper.py` and `tests/integration/test_amc_stonebriar_ingestion.py`.
4. Deploy MVP for basic showtime capture (single day, no format/ticket-link detail).

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (AMC Stonebriar 24 cinema registered, dispatch wired, app bootstrap updated, bot-gate detection in place).
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!).
3. Add User Story 2 → Test independently → Deploy/Demo.
4. Add User Story 3 → Test independently → Deploy/Demo.
5. Each story adds value without breaking previous stories or the existing Cinepolis/Texas Theatre/Angelika Dallas sources.

---

## Notes

- [P] tasks = different files, no dependencies.
- [Story] label maps task to specific user story for traceability.
- T003 (live DOM/date-mechanism inspection) is unusually load-bearing: research.md explicitly left the session-id attribute and the multi-day date-walk mechanism unresolved because they require observing real rendered markup/network traffic, not static analysis (constitution VII). All of Phase 3–5 implementation tasks assume T003's findings are available.
- FR-008 (TMDB rating fallback) requires no new task: it is already implemented source-agnostically in `enrich.py`/`storage.py` (research.md §6) and applies automatically once AMC Stonebriar 24 showtimes are ingested.
- Commit after each task or logical group.
- Stop at any checkpoint to validate story independently.
