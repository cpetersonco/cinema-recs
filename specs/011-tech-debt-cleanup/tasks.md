# Tasks: Tech Debt Cleanup — Cinema Routing, Deprecated APIs, Startup Coverage

**Input**: Design documents from `/specs/011-tech-debt-cleanup/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. No Setup/Foundational phase — all three findings touch a small, mostly non-overlapping set of existing files (plan.md), and User Story 1 (routing) is implemented first per the spec's own priority order since User Story 3's tests assert on the `source_type` field it introduces.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: User Story 1 - Fail loudly on an unrecognized cinema source instead of silently misrouting (Priority: P1) 🎯 MVP

**Goal**: `Cinema` gains an explicit `source_type` field set at creation time; `run_ingestion` dispatches on it and fails clearly for any unrecognized value instead of defaulting to the Cinepolis scraper; existing rows are backfilled automatically.

**Independent Test**: Configure a cinema whose source doesn't match any known scraper, trigger an ingestion run for it, and confirm the run fails with a clear, specific error — not a "successful" run using the wrong scraper.

### Tests for User Story 1

- [X] T001 [P] [US1] Unit test: `get_or_create_cinema` persists a `source_type` value (defaulting to `"cinepolis"` when the caller doesn't pass one — preserving today's implicit "generic source" behavior for existing callers — and storing whatever explicit value is passed otherwise), in `tests/unit/test_storage.py`
- [X] T002 [P] [US1] Unit test: the new migration backfills `source_type` for cinema rows created before this column existed, using the same substring-matching rules `ingest.py`'s old dispatch used (`thetexastheatre.com`/`"texas theatre"` → `"texas_theatre"`; `angelikafilmcenter.com`/`"angelika"` → `"angelika_dallas"`; else → `"cinepolis"`), in `tests/unit/test_storage.py`
- [X] T003 [P] [US1] Unit test: `run_ingestion` dispatches to the correct scraper (`scrape_showtimes` / `scrape_texas_theatre_showtimes` / `scrape_angelika_dallas_showtimes`) based on `cinema.source_type` alone, for all 3 known values, in `tests/unit/test_ingest.py`
- [X] T004 [P] [US1] Unit test: `run_ingestion` for a cinema with an unrecognized `source_type` fails immediately with `outcome="failure"` and an `error_message` naming the unrecognized value, without calling any scraper function, in `tests/unit/test_ingest.py`

### Implementation for User Story 1

- [X] T005 [US1] Add `source_type: str` to the `Cinema` dataclass in `src/cinema_recs/models.py`
- [X] T006 [US1] Add `source_type TEXT NOT NULL DEFAULT 'cinepolis'` to the `cinema` table in `SCHEMA`, and add a new `_migrate_add_cinema_source_type(conn)` migration function in `src/cinema_recs/storage.py` (called from `init_schema`, alongside the existing two migrations) that adds the column if absent and backfills every row where it's unset using the retiring substring-matching rules (data-model.md)
- [X] T007 [US1] Add a `source_type: str = "cinepolis"` keyword parameter to `get_or_create_cinema` in `src/cinema_recs/storage.py`; include it in the `INSERT`/`UPDATE` SQL and in every `Cinema(...)` construction in that function
- [X] T008 [US1] Update `ensure_texas_theatre_cinema`/`ensure_angelika_dallas_cinema` in `src/cinema_recs/storage.py` to pass `source_type="texas_theatre"`/`source_type="angelika_dallas"` explicitly to `get_or_create_cinema`
- [X] T009 [US1] Update `main.py`'s `bootstrap()` to pass `source_type="cinepolis"` explicitly on its `get_or_create_cinema` call for the Cinepolis cinema (explicit per FR-001, even though it matches the default)
- [X] T010 [US1] Replace the if/elif/else substring-matching dispatch in `run_ingestion` (`src/cinema_recs/ingest.py`) with an explicit mapping from `cinema.source_type` to its scraper function (`{"cinepolis": scrape_showtimes, "texas_theatre": scrape_texas_theatre_showtimes, "angelika_dallas": scrape_angelika_dallas_showtimes}`); raise a `ValueError` naming the unrecognized `source_type` when it's not a key in that mapping, letting the function's existing `except Exception` handler record it as `outcome="failure"` with that message, exactly like any other scrape failure today

**Checkpoint**: At this point, User Story 1 is fully functional and testable independently — cinema routing is explicit and unrecognized sources fail loudly (MVP ready)

---

## Phase 2: User Story 2 - Stop relying on a deprecated timestamp API (Priority: P2)

**Goal**: No code in the application calls the deprecated `datetime.utcnow()`; every timestamp produced is behaviorally identical to before.

**Independent Test**: Run the full automated test suite and confirm no deprecation warnings reference the old UTC timestamp API, while all timestamp-dependent behavior is unchanged.

### Tests for User Story 2

- [X] T011 [P] [US2] Record the current full-suite deprecation-warning count as a baseline (`PYTHONPATH=src pytest tests/ -q 2>&1 | grep -c "datetime.utcnow"` or equivalent) before making any change in this story, to verify against after T012-T014 — no file changes, verification prep only

### Implementation for User Story 2

- [X] T012 [P] [US2] Replace all 3 `datetime.utcnow()` call sites in `src/cinema_recs/ingest.py` with `datetime.now(timezone.utc).replace(tzinfo=None)` (research.md §2); add `timezone` to the file's `from datetime import ...` line
- [X] T013 [P] [US2] Replace all 6 `datetime.utcnow()` call sites in `src/cinema_recs/storage.py` with `datetime.now(timezone.utc).replace(tzinfo=None)`; add `timezone` to the file's `from datetime import ...` line
- [X] T014 [P] [US2] Replace the 1 `datetime.utcnow()` call site in `src/cinema_recs/notify.py` with `datetime.now(timezone.utc).replace(tzinfo=None)`; add `timezone` to the file's `from datetime import ...` line
- [X] T015 [US2] Verify: run the full test suite and confirm zero warnings reference the old UTC timestamp API (down from the T011 baseline) and the total pass count is unchanged from before this story

**Checkpoint**: User Stories 1 AND 2 both work independently — routing is explicit and the deprecated timestamp API is gone

---

## Phase 3: User Story 3 - Verify the app's startup wiring is actually correct (Priority: P2)

**Goal**: `main.py`'s cinema-assembly and CLI-mode logic is covered by automated tests that run fully offline.

**Independent Test**: Run the test suite and confirm it includes passing tests that exercise which cinemas get configured and what each supported CLI mode does, without hitting real network or starting a real server.

### Tests for User Story 3

- [X] T016 [US3] Create `tests/unit/test_main.py` with a test for `bootstrap()`: given required env vars set via `monkeypatch.setenv` (mirroring `tests/unit/test_config.py`'s conventions) and a `tmp_path` data dir, assert all 3 cinemas (Cinepolis, Texas Theatre, Angelika Dallas) come back with their correct `source_type` (per US1's T005-T009) and that `init_schema` was applied
- [X] T017 [US3] Add a test to `tests/unit/test_main.py` for `main()`'s `ingest-once` CLI branch (`sys.argv = ["main.py", "ingest-once"]`): monkeypatch `scrape_showtimes`/`scrape_texas_theatre_showtimes`/`scrape_angelika_dallas_showtimes` (as `tests/unit/test_ingest.py` already does) and the network-calling seams of enrichment/recommendation/notification (TMDB client, Letterboxd client, Discord client — as `test_enrich.py`/`test_recommend.py`/`test_notify.py` already do), then assert `main()` returns without calling `start_scheduler` or `Flask.run`
- [X] T018 [US3] Add a test to `tests/unit/test_main.py` for `main()`'s default (no-args) branch: same mocking as T017, plus monkeypatch `cinema_recs.scheduler.start_scheduler` and the returned Flask app's `.run` method to no-op spies, then assert both were called once with the expected `config`/`cinemas` arguments

**Checkpoint**: All user stories are independently functional — routing is explicit, the deprecated API is gone, and startup wiring has coverage

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Validate the complete feature end-to-end

- [X] T019 Run `quickstart.md`'s full validation sequence (steps 1-5) — steps 1-2 (migration backfill, loud failure on unrecognized source) verified live: all 3 real cinemas get correct source_type, an unrecognized source_type fails with a clear ValueError message and outcome="failure"; steps 3-5 (no deprecation warnings, startup coverage, no regressions) verified via the automated suite (163/163 passing)
- [X] T020 [P] Run `ruff check` on every file touched by this feature (`models.py`, `storage.py`, `ingest.py`, `notify.py`, `main.py`, `test_storage.py`, `test_ingest.py`, `test_main.py`) and confirm no *new* lint findings were introduced — the 49 pre-existing `E501` findings elsewhere in the repo remain explicitly out of scope for this feature (spec Assumptions) — repo-wide count is now 48 (net -1, after fixing long lines introduced in test_ingest.py's dispatch tests during authoring), confirming zero new debt

---

## Dependencies & Execution Order

### Phase Dependencies

- **User Story 1 (Phase 1)**: No dependencies — can start immediately; delivers the MVP (explicit routing, loud failure on unrecognized sources)
- **User Story 2 (Phase 2)**: No dependency on User Story 1 — independently implementable and testable, touches different lines in shared files
- **User Story 3 (Phase 3)**: Independently testable per spec, but its `bootstrap()` test (T016) asserts on the `source_type` field User Story 1 introduces — implement after User Story 1 so that assertion has something real to check
- **Polish (Phase 4)**: Depends on all three stories being complete

### Within Each User Story

- Tests before implementation (write and confirm failing first)
- Story complete before moving to next priority

### Parallel Opportunities

- T001-T004 (US1 tests) can run in parallel — different test functions, though T003/T004 depend on T005-T010 existing to pass (write them first per TDD, expect them to fail until implementation lands)
- T012, T013, T014 (US2 implementation) touch different files and can be done in parallel
- T007 and T008 both touch `storage.py` but different functions — implement sequentially to avoid merge conflicts within the same file, per the pattern already used in prior features' task lists

---

## Parallel Example: User Story 1

```bash
# Launch all User Story 1 tests together:
Task: "Unit test: get_or_create_cinema persists source_type in tests/unit/test_storage.py"
Task: "Unit test: migration backfills source_type for existing rows in tests/unit/test_storage.py"
Task: "Unit test: run_ingestion dispatches on cinema.source_type in tests/unit/test_ingest.py"
Task: "Unit test: run_ingestion fails loudly for unrecognized source_type in tests/unit/test_ingest.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: User Story 1 (T001-T010)
2. **STOP and VALIDATE**: Run quickstart.md steps 1-2 independently — confirms the core routing/reliability fix works and existing deployments upgrade cleanly
3. Deploy/demo if ready

### Incremental Delivery

1. Add User Story 1 → validate via quickstart steps 1-2 (MVP!)
2. Add User Story 2 → validate via quickstart step 3 (no deprecation warnings)
3. Add User Story 3 → validate via quickstart step 4 (startup wiring coverage)
4. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files or independent functions, no dependencies
- [Story] label maps task to specific user story for traceability
- `get_or_create_cinema`'s new `source_type` parameter defaults to `"cinepolis"` specifically so the many existing test fixtures across the suite that call it without a type (`test_ingest.py`, `test_enrich.py`, `test_notify.py`, `test_ingestion.py`, `test_full_window_notifications.py`, `test_web_view.py`) keep working unchanged — only the tests added/modified in this feature (T001-T004, T016-T018) need to pass it explicitly
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- After implementation, run `graphify update .` per the `after_implement` hook in `.specify/extensions.yml` (dispatched automatically by `/speckit-implement`)
