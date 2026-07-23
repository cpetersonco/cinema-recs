# Tasks: Texas Theatre Showtime Source Ingestion

**Input**: Design documents from `/specs/006-texas-theatre-source/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/scraper_interface.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Venue configuration and database initialization helpers

- [x] T001 Define Texas Theatre URL and default venue configuration constants in `src/cinema_recs/config.py`
- [x] T002 [P] Add Texas Theatre cinema record helper/seeder in `src/cinema_recs/storage.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Scraper function stub and ingestion routing setup

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Implement `scrape_texas_theatre_showtimes()` scraper function stub in `src/cinema_recs/scraper.py`
- [x] T004 Register Texas Theatre scraper dispatch routing in `src/cinema_recs/ingest.py`

**Checkpoint**: Foundational scraper routing established.

---

## Phase 3: User Story 1 - Ingest upcoming showtimes from Texas Theatre calendar (Priority: P1) 🎯 MVP

**Goal**: Fetch published calendar events from `https://thetexastheatre.com/calendar`, parse screening dates, titles, and start times, and store showtime records idempotently in SQLite.

**Independent Test**: Trigger ingestion for Texas Theatre source and verify showtimes stored in `cinema.db`.

### Tests for User Story 1

- [x] T005 [P] [US1] Unit test for Texas Theatre calendar HTML fetching & date/time parsing in `tests/unit/test_texas_theatre_scraper.py`
- [x] T008 [P] [US1] Integration test for Texas Theatre showtime ingestion run in `tests/integration/test_texas_theatre_ingestion.py`

### Implementation for User Story 1

- [x] T006 [US1] Implement Playwright fetching and HTML calendar event parsing in `src/cinema_recs/scraper.py`
- [x] T007 [US1] Connect Texas Theatre scraper result to storage upsert in `src/cinema_recs/ingest.py`

**Checkpoint**: At this point, User Story 1 is fully functional and testable independently (MVP ready).

---

## Phase 4: User Story 2 - Capture film screening formats and ticket links (Priority: P2)

**Goal**: Extract specialty presentation formats (35mm, 70mm, 16mm, Digital) and event ticketing links into showtime records.

**Independent Test**: Verify ingested records with format tags and ticket links match calendar page content.

### Tests for User Story 2

- [x] T009 [P] [US2] Unit test for projection format regex extraction (35mm, 70mm, 16mm, Digital) in `tests/unit/test_texas_theatre_scraper.py`

### Implementation for User Story 2

- [x] T010 [US2] Implement format regex pattern extraction and ticket URL parsing in `src/cinema_recs/scraper.py`
- [x] T011 [US2] Propagate parsed format string and ticket URL to `Showtime` dataclass in `src/cinema_recs/ingest.py`

**Checkpoint**: User Story 2 features (projection format and ticket link capture) complete and independently testable.

---

## Phase 5: User Story 3 - Synchronize calendar updates and cancellations (Priority: P3)

**Goal**: Refresh existing showtimes, update modified event details, and mark omitted showtimes as stale.

**Independent Test**: Re-run ingestion after source updates and verify stored records accurately reflect additions/removals.

### Tests for User Story 3

- [x] T012 [P] [US3] Integration test for stale showtime reconciliation on calendar updates in `tests/integration/test_texas_theatre_ingestion.py`

### Implementation for User Story 3

- [x] T013 [US3] Verify stale showtime marking and partial/failure run status reporting for Texas Theatre in `src/cinema_recs/ingest.py`

**Checkpoint**: All user stories complete and functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final logging, documentation verification, and validation scenarios

- [x] T014 [P] Add structured logging for Texas Theatre ingestion progress, Cloudflare blocks, and error handling in `src/cinema_recs/scraper.py`
- [x] T015 Execute end-to-end validation scenarios documented in `specs/006-texas-theatre-source/quickstart.md`

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
- **User Story 2 (P2)**: Extends US1 scraper parsing logic.
- **User Story 3 (P3)**: Extends US1 ingestion storage lifecycle.

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Complete Phase 1 (Setup) and Phase 2 (Foundational).
2. Complete Phase 3 (User Story 1).
3. Validate User Story 1 using `tests/unit/test_texas_theatre_scraper.py` and `tests/integration/test_texas_theatre_ingestion.py`.
4. Deploy MVP for basic showtime capture.
