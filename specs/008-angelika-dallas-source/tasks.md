# Tasks: Angelika Film Center Dallas Showtime Ingestion Source

**Input**: Design documents from `/specs/008-angelika-dallas-source/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/scraper_interface.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Venue configuration constants and database registration helper

- [X] T001 Define `ANGELIKA_DALLAS_NAME`, `ANGELIKA_DALLAS_LOCATION`, `ANGELIKA_DALLAS_DEFAULT_URL` constants in `src/cinema_recs/config.py` (mirrors existing `TEXAS_THEATRE_*` constants)
- [X] T002 [P] Add `ensure_angelika_dallas_cinema(db_path)` cinema record helper/seeder in `src/cinema_recs/storage.py` (mirrors `ensure_texas_theatre_cinema`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Scraper function stub, ingestion routing, and application wiring

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Inspect live network traffic against `https://angelikafilmcenter.com/dallas` (Playwright-driven browser or devtools) to confirm the Reading Cinemas `production-api.readingcinemas.com` sessions/showtimes endpoint path, required headers/auth, and the Dallas venue's `cinemaId`, per research.md §1; record findings as code comments in `src/cinema_recs/scraper.py` (same documentation style as the existing Cinepolis `MCKINNEY_SITE_ID`/`CINEPOLIS_CIRCUIT_ID` header comment)
- [X] T004 Implement `scrape_angelika_dallas_showtimes()` scraper function stub (signature per `contracts/scraper_interface.md`) in `src/cinema_recs/scraper.py`
- [X] T005 Register Angelika Dallas scraper dispatch routing (`"angelikafilmcenter.com"` domain match) in `run_ingestion()` in `src/cinema_recs/ingest.py`
- [X] T006 Wire `ensure_angelika_dallas_cinema()` into `bootstrap()`'s `cinemas` list in `main.py`, alongside the existing Cinepolis and Texas Theatre cinemas, so ingestion/enrichment/notifications/scheduler/web view all pick up the new source

**Checkpoint**: Foundational scraper routing and app wiring established.

---

## Phase 3: User Story 1 - Ingest upcoming showtimes from Angelika Film Center Dallas (Priority: P1) 🎯 MVP

**Goal**: Fetch published showtimes from the Reading Cinemas API for the Angelika Dallas venue, parse film titles/dates/start times, exclude non-film events, and store showtime records idempotently in SQLite.

**Independent Test**: Trigger ingestion for the Angelika Dallas source and verify showtimes are stored in `cinema.db` per `quickstart.md` Scenario 1.

### Tests for User Story 1

- [X] T007 [P] [US1] Unit test for Angelika Dallas API response fetching & date/time parsing in `tests/unit/test_angelika_dallas_scraper.py`
- [X] T008 [P] [US1] Integration test for Angelika Dallas showtime ingestion run in `tests/integration/test_angelika_dallas_ingestion.py`

### Implementation for User Story 1

- [X] T009 [US1] Implement `fetch_angelika_dallas_sessions()` API/network fetch (with retry/backoff and `BlockedError` handling, matching existing `fetch_showings_json`/`fetch_texas_theatre_html` patterns) in `src/cinema_recs/scraper.py`
- [X] T010 [US1] Implement `parse_angelika_dallas_sessions()` to map API session records to `ScrapedShowtime` (title, show_date, start_time in `CENTRAL_TIME`) in `src/cinema_recs/scraper.py`
- [X] T011 [US1] Implement film-screening vs. non-film-event classification/filtering (structured API field if available, else title-keyword fallback per research.md §5) in `parse_angelika_dallas_sessions()` in `src/cinema_recs/scraper.py`, satisfying spec FR-008
- [X] T012 [US1] Complete `scrape_angelika_dallas_showtimes()` to call fetch + parse and return `ScrapeResult` (`reported_count` reflecting skipped/filtered entries) in `src/cinema_recs/scraper.py`

**Checkpoint**: At this point, User Story 1 is fully functional and testable independently (MVP ready).

---

## Phase 4: User Story 2 - Capture screening formats and ticket links (Priority: P2)

**Goal**: Extract presentation format (e.g. Standard, 3D, Special Event) and direct ticket purchase links into showtime records.

**Independent Test**: Ingest a listing with a non-default format and verify the stored record's `format` and `ticket_url` match the source, per `quickstart.md` Scenario 2.

### Tests for User Story 2

- [X] T013 [P] [US2] Unit test for presentation format extraction and ticket URL parsing in `tests/unit/test_angelika_dallas_scraper.py`

### Implementation for User Story 2

- [X] T014 [US2] Implement presentation format extraction from the session API's format/attribute field (with title-text fallback if the field is unreliable, per research.md §2) in `parse_angelika_dallas_sessions()` in `src/cinema_recs/scraper.py`
- [X] T015 [US2] Implement ticket/detail URL extraction or construction from the session API response in `parse_angelika_dallas_sessions()` in `src/cinema_recs/scraper.py`

**Checkpoint**: User Story 2 features (format and ticket link capture) complete and independently testable.

---

## Phase 5: User Story 3 - Synchronize schedule updates and cancellations (Priority: P3)

**Goal**: Refresh existing Angelika Dallas showtimes on each ingestion run, update modified event details, and mark removed showtimes as stale.

**Independent Test**: Re-run ingestion after a simulated schedule change and verify stored records accurately reflect additions/removals/updates, per `quickstart.md` Scenario 3.

### Tests for User Story 3

- [X] T016 [P] [US3] Integration test for stale showtime reconciliation and repeated-run idempotency in `tests/integration/test_angelika_dallas_ingestion.py`

### Implementation for User Story 3

- [X] T017 [US3] Verify stale showtime marking (`storage.mark_stale_showtimes`) and partial/failure `IngestionRun` outcome reporting behave correctly for Angelika Dallas API errors/partial parses in `src/cinema_recs/ingest.py` and `src/cinema_recs/scraper.py`

**Checkpoint**: All user stories complete and functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final logging, documentation verification, and validation scenarios

- [X] T018 [P] Add structured logging for Angelika Dallas ingestion progress, API/auth errors, and bot-block detection in `src/cinema_recs/scraper.py`
- [X] T019 Execute end-to-end validation scenarios documented in `specs/008-angelika-dallas-source/quickstart.md`

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
- **User Story 2 (P2)**: Extends US1 scraper parsing logic (`parse_angelika_dallas_sessions()`).
- **User Story 3 (P3)**: Extends US1 ingestion storage lifecycle; verification-only, no new parsing logic.

### Parallel Opportunities

- T001 and T002 (Phase 1) can run in parallel (different files).
- T007 and T008 (US1 tests) can run in parallel (different test files).
- T018 (Polish logging) can run in parallel with T019 (manual validation) once all stories are complete.

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for Angelika Dallas API response fetching & date/time parsing in tests/unit/test_angelika_dallas_scraper.py"
Task: "Integration test for Angelika Dallas showtime ingestion run in tests/integration/test_angelika_dallas_ingestion.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational) — including the live API inspection task (T003), which is a hard prerequisite for any real parsing work.
2. Complete Phase 3 (User Story 1).
3. Validate User Story 1 using `tests/unit/test_angelika_dallas_scraper.py` and `tests/integration/test_angelika_dallas_ingestion.py`.
4. Deploy MVP for basic showtime capture.

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (Angelika Dallas cinema registered, dispatch wired, app bootstrap updated).
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!).
3. Add User Story 2 → Test independently → Deploy/Demo.
4. Add User Story 3 → Test independently → Deploy/Demo.
5. Each story adds value without breaking previous stories or the existing Cinepolis/Texas Theatre sources.

---

## Notes

- [P] tasks = different files, no dependencies.
- [Story] label maps task to specific user story for traceability.
- T003 (live API inspection) is unusually load-bearing: research.md left the exact endpoint/auth/`cinemaId` unresolved because it requires observing real network traffic, not static analysis. All of Phase 3–5 implementation tasks assume T003's findings are available.
- Commit after each task or logical group.
- Stop at any checkpoint to validate story independently.
