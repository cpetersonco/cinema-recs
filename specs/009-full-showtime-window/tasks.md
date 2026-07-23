# Tasks: Full Showtime Window Ingestion

**Input**: Design documents from `/specs/009-full-showtime-window/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the shared "fetch completeness" plumbing every story builds on

- [X] T001 Add a `complete: bool` field to the `ScrapeResult` NamedTuple in `src/cinema_recs/scraper.py` (defaulting `True` for existing single-call sources until each is updated), so callers can tell "fetched everything currently published" apart from "stopped early due to an error"

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Gate `run_ingestion`'s stale-marking on fetch completeness — this is required by every user story since it's what makes a wider fetch window safe

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 In `src/cinema_recs/ingest.py`, change `run_ingestion` to only call `storage.mark_stale_showtimes` when `result.complete` is `True`; when `False`, skip stale-marking, set `outcome` to `"failure"` (or `"partial"` if some showtimes were still captured before the walk stopped), and populate `error_message` describing which page/date/month the walk failed on (data-model.md: `IngestionRun.error_message`)
- [X] T003 [P] Update `tests/integration/test_texas_theatre_ingestion.py` and `tests/integration/test_angelika_dallas_ingestion.py` fixtures/mocks that construct `ScrapeResult` directly to pass the new `complete` field so existing tests keep passing against the changed signature — verified unnecessary: `complete` defaults to `True` on `ScrapeResult` (T001), and all existing direct constructions are keyword-based, so the full suite (43 tests) already passes unchanged

**Checkpoint**: `run_ingestion` now trusts a `complete` flag before stale-marking; each source's scraper can now be updated independently to set that flag honestly

---

## Phase 3: User Story 1 - See every showtime a source has published, not just the next day or month (Priority: P1) 🎯 MVP

**Goal**: Each of the three scrapers (Cinepolis, Texas Theatre, Angelika Dallas) fetches its source's complete currently-published showtime calendar in one ingestion run, per research.md's per-source walk strategy.

**Independent Test**: Run ingestion for a cinema whose source currently publishes showtimes across multiple future dates/months (per quickstart.md step 1) and confirm showtimes from all of them are captured in that single run.

### Tests for User Story 1

- [X] T004 [P] [US1] Unit test: `fetch_showings_json`/date-loop for Cinepolis reuses one browser/page across multiple dates and stops after 2 consecutive `count == 0` dates, in `tests/unit/test_scraper.py`
- [X] T005 [P] [US1] Unit test: Texas Theatre month-walk follows the page's own "next month" link forward and stops after 2 consecutive zero-listing months (research.md §2's non-monotonic Sep=4/Oct=5 case), in `tests/unit/test_texas_theatre_scraper.py`
- [X] T006 [P] [US1] Integration test: a full Cinepolis ingestion run captures showtimes dated beyond tomorrow in one run, in `tests/integration/test_ingestion.py` (or the Cinepolis-specific integration test file)
- [X] T007 [P] [US1] Integration test: a full Texas Theatre ingestion run captures showtimes beyond the current calendar month in one run, in `tests/integration/test_texas_theatre_ingestion.py`

### Implementation for User Story 1

- [X] T008 [US1] Refactor `fetch_showings_json`/`scrape_showtimes` in `src/cinema_recs/scraper.py` to launch one Playwright browser/page per run, loop `page.evaluate` GraphQL calls forward one date at a time starting today, and stop after 2 consecutive dates report `count == 0` (research.md §1); set `ScrapeResult.complete = True` only if the loop reached its own stop condition, `False` if a fetch attempt exhausted its retries partway through
- [X] T009 [US1] Refactor `fetch_texas_theatre_html`/`scrape_texas_theatre_showtimes` in `src/cinema_recs/scraper.py` to walk forward from the current month via the calendar page's own "next month" link, accumulating `parse_texas_theatre_html` results, stopping after 2 consecutive zero-listing months (research.md §2); set `ScrapeResult.complete` accordingly
- [X] T010 [US1] Live-verify (during implementation, via the existing `page.expect_response` capture in `fetch_angelika_dallas_films`) whether the `/films` response's `showdates` array already covers Angelika Dallas's full published window, per research.md §3; if confirmed, leave `scrape_angelika_dallas_showtimes` as a single call with `complete = True`; if a narrower window than the source publishes is found, apply the same "walk until N empty periods" pattern used for Texas Theatre using whatever pagination the live request reveals — **live verification found the original assumption wrong**: `/films` is per-date (`selectedDate` query param), not multi-date. Implemented a click-driven walk of the site's own `div#anytime` date-selector strip instead of a heuristic stop condition (research.md §3, corrected). Live smoke test: 858 showtimes across 76 dates (2026-07-23 → 2027-01-12), `complete=True`, ~65s
- [X] T011 [US1] Update `run_ingestion` in `src/cinema_recs/ingest.py` to log the number of dates/months walked and the final `complete` value for each cinema's run, consistent with existing logging (Constitution V)

**Checkpoint**: At this point, User Story 1 is fully functional and testable independently — a single ingestion run per source captures its complete published calendar

---

## Phase 4: User Story 2 - Stop false cancellation/reschedule alerts caused by a narrow fetch window (Priority: P1)

**Goal**: A showtime dated beyond what a prior narrow-window run would have re-touched stays `active` (and triggers no false cancellation/reschedule alert) as long as the source still publishes it, once full-window fetching (User Story 1) and completeness-gated stale-marking (Phase 2) are both in place.

**Independent Test**: Seed a showtime dated several weeks out that a narrow-window run would have missed, run full-window ingestion, and confirm it stays `active` with no Discord cancellation/reschedule notification (quickstart.md step 3).

### Tests for User Story 2

- [X] T012 [P] [US2] Integration test: a showtime dated 3+ weeks out that is still published by the source remains `active` (not `stale`) after a full-window ingestion run, and feature 005's notification logic sends no cancellation/reschedule alert for it, in `tests/integration/test_full_window_notifications.py`
- [X] T013 [P] [US2] Integration test: a showtime genuinely no longer present anywhere in a source's full published calendar is still marked `stale` and still triggers feature 005's existing cancellation/reschedule notification exactly as before, in `tests/integration/test_full_window_notifications.py`

### Implementation for User Story 2

- [X] T014 [US2] Verify (add a regression assertion if not already covered by T002/T003) that `mark_stale_showtimes` in `src/cinema_recs/storage.py` is being invoked with the full-window `started_at` timestamp only after all of a cinema's walked pages/dates/months have been folded into storage via `upsert_showtime`, not per-page, per data-model.md's "State transitions (unchanged)" note — confirmed by inspection: `run_ingestion` (ingest.py) loops `storage.upsert_showtime` over the scraper's full accumulated `result.showtimes` list first, then calls `mark_stale_showtimes` once afterward, only when `result.complete` is `True` (T002); T012/T013 exercise this end-to-end

**Checkpoint**: User Stories 1 AND 2 both work independently — full-window fetching is in place and stale-marking only trusts a completed walk

---

## Phase 5: User Story 3 - Ingestion stays reliable when a source's full calendar is large or slow to fetch (Priority: P2)

**Goal**: A mid-walk failure (source becomes unavailable after some but not all pages/dates succeed) is recorded as a `failure`/`partial` ingestion run without marking any previously-active showtime stale.

**Independent Test**: Simulate a source becoming unavailable partway through its full-window fetch and confirm the ingestion run is recorded as `failure`/`partial` with no showtimes marked stale for that cinema (quickstart.md step 5).

### Tests for User Story 3

- [X] T015 [P] [US3] Unit test: Cinepolis date-loop that fails (retries exhausted) on, say, the 4th date returns `ScrapeResult(complete=False, ...)` with the showtimes captured from the first 3 dates preserved, in `tests/unit/test_scraper.py` — implemented in T004's `test_walk_cinepolis_dates_marks_incomplete_when_a_date_fails`
- [X] T016 [P] [US3] Unit test: Texas Theatre month-walk that fails fetching a subsequent month page returns `ScrapeResult(complete=False, ...)` with prior months' showtimes preserved, in `tests/unit/test_texas_theatre_scraper.py` — implemented in T005's `test_walk_texas_theatre_months_marks_incomplete_when_a_month_fails`
- [X] T017 [P] [US3] Integration test: an ingestion run where the source fails partway through the full-window walk is recorded with `outcome` `"failure"` or `"partial"` and a descriptive `error_message` naming the failed page/date, and no previously-active showtime for that cinema is marked `stale`, in `tests/integration/test_ingestion.py`

### Implementation for User Story 3

- [X] T018 [US3] In the Cinepolis date-loop (`src/cinema_recs/scraper.py`, from T008), catch a fetch failure on any individual date after retries are exhausted, stop the loop, and return `ScrapeResult(showtimes=<accumulated so far>, complete=False, ...)` instead of propagating the exception past the loop
- [X] T019 [US3] In the Texas Theatre month-walk (`src/cinema_recs/scraper.py`, from T009), catch a fetch failure on any individual month page after retries are exhausted, stop the walk, and return `ScrapeResult(showtimes=<accumulated so far>, complete=False, ...)` instead of propagating the exception past the loop
- [X] T020 [US3] Confirm `run_ingestion` in `src/cinema_recs/ingest.py` (per T002) correctly sets `error_message` to identify the failed page/date/month when `complete=False`, using whatever detail the scraper's returned exception/context provides — same mechanism also covers Angelika Dallas's date-strip walk (T010) via `_walk_angelika_dallas_dates`'s `incomplete_reason`

**Checkpoint**: All user stories are independently functional — full-window fetch, false-alert prevention, and mid-walk failure safety

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate the complete feature end-to-end and keep the knowledge graph current

- [X] T021 Run `quickstart.md`'s full validation sequence (steps 1-5) against a real or locally-run container — steps 1-2 (capture beyond narrow window, self-terminating walk) verified live against all three real sources: Cinepolis (493 showtimes/28 dates/~19s), Texas Theatre (72 showtimes/29 dates spanning Jul-Oct/~3.6s), Angelika Dallas (858 showtimes/76 dates spanning Jul 2026-Jan 2027/~65s), all `complete=True`; steps 3-5 (no false alert, genuine alert still fires, partial-failure safety) verified via the automated integration test suite (T006/T007/T012/T013/T017), which exercises the same `run_ingestion`/`run_notifications` code paths against a real SQLite DB with mocked scrapers
- [X] T022 [P] Review `src/cinema_recs/scraper.py` logging added across T008/T009/T018/T019 for consistency with existing log message style (Constitution V) — found and fixed an inconsistency: `scrape_showtimes` (Cinepolis) was missing the start/completion `logger.info` pair that Texas Theatre and Angelika Dallas already had; added matching "Starting.../...scrape complete" log lines

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001's `complete` field) — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — delivers the core fetch-everything behavior; no dependency on US2/US3
- **User Story 2 (Phase 4)**: Depends on Foundational; in practice also depends on User Story 1's per-source loops existing (T008/T009) to have real multi-date/month data to test against, though its own logic (T014) is about stale-marking, not fetching
- **User Story 3 (Phase 5)**: Depends on Foundational; extends the same loops User Story 1 built (T008/T009) with failure handling — implement after US1
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### Within Each User Story

- Tests before implementation (write and confirm failing first)
- Cinepolis and Texas Theatre implementation tasks (T008/T009, T018/T019) touch the same file (`scraper.py`) but different functions — safe to parallelize across sources, not within one source's task sequence
- Story complete before moving to next priority

### Parallel Opportunities

- T004-T007 (US1 tests) can run in parallel — different files/functions
- T008 (Cinepolis) and T009 (Texas Theatre) can be implemented in parallel by different sessions — independent functions in the same file, low conflict risk if merged carefully
- T012-T013 (US2 tests) can run in parallel
- T015-T017 (US3 tests) can run in parallel
- T018 and T019 can be implemented in parallel (mirrors T008/T009)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test: Cinepolis date-loop reuse + stop condition in tests/unit/test_scraper.py"
Task: "Unit test: Texas Theatre month-walk + stop condition in tests/unit/test_texas_theatre_scraper.py"
Task: "Integration test: full Cinepolis run captures dates beyond tomorrow in tests/integration/test_ingestion.py"
Task: "Integration test: full Texas Theatre run captures dates beyond this month in tests/integration/test_texas_theatre_ingestion.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002-T003) — CRITICAL, blocks all stories
3. Complete Phase 3: User Story 1 (T004-T011)
4. **STOP and VALIDATE**: Run quickstart.md steps 1-2 independently
5. Deploy/demo if ready — this alone fixes the core "narrow window" problem, though User Story 2's false-alert-prevention guarantee isn't fully proven without its own tests

### Incremental Delivery

1. Complete Setup + Foundational → completeness signal wired through stale-marking
2. Add User Story 1 → full-window fetch works → validate via quickstart steps 1-2 (MVP!)
3. Add User Story 2 → validate no false alerts via quickstart step 3-4
4. Add User Story 3 → validate failure safety via quickstart step 5
5. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files or independent functions, no dependencies
- [Story] label maps task to specific user story for traceability
- Angelika Dallas (T010) is deliberately the lightest-touch source per research.md §3 — its existing single-call fetch is already believed to satisfy User Story 1, pending live confirmation during implementation; do not add pagination logic to it unless that confirmation shows it's needed (Constitution IV)
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- After implementation, run `graphify update .` per the `after_implement` hook in `.specify/extensions.yml` (dispatched automatically by `/speckit-implement`)
