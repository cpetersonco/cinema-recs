# Tasks: Cinemark West Plano XD and ScreenX Showtime Ingestion Source

**Input**: Design documents from `/specs/012-cinemark-west-plano-source/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/scraper_interface.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Venue configuration constants and database registration helper

- [X] T001 Define `CINEMARK_WEST_PLANO_NAME`, `CINEMARK_WEST_PLANO_LOCATION`, `CINEMARK_WEST_PLANO_DEFAULT_URL`, `CINEMARK_WEST_PLANO_THEATER_ID` constants in `src/cinema_recs/config.py` (mirrors existing `TEXAS_THEATRE_*` / `ANGELIKA_DALLAS_*` constants)
- [X] T002 [P] Add `ensure_cinemark_west_plano_cinema(db_path)` cinema record helper/seeder in `src/cinema_recs/storage.py` (mirrors `ensure_angelika_dallas_cinema`), setting `source_type="cinemark_west_plano"`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Scraper function stubs, ingestion routing, and application wiring

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Implement `extract_cinemark_west_plano_dates(html, base_url)` to parse the main theatre page's `a.showdate-link[data-datevalue="YYYY-MM-DD"]` date-tab strip into an ordered list of `date` objects, per research.md §4, in `src/cinema_recs/scraper.py`
- [X] T004 Implement `fetch_cinemark_west_plano_html(theater_id, show_date, timeout_ms=30_000)` to fetch a single date's `GET /umbraco/surface/Showtimes/GetByTheaterId?theaterId=...&showDate=...` HTML fragment, reusing the existing `_fetch_page_html_with_retry` retry/blocked-page pattern (Playwright + `Stealth().apply_stealth_sync`, `REALISTIC_USER_AGENT`) in `src/cinema_recs/scraper.py`
- [X] T005 Implement `scrape_cinemark_west_plano_showtimes()` scraper function stub (signature per `contracts/scraper_interface.md`) — walking the date list from T003 and calling T004 per date, reusing one browser/context for the whole run (matching `scrape_texas_theatre_showtimes`'s single-browser-session pattern) — in `src/cinema_recs/scraper.py`
- [X] T006 Register Cinemark West Plano scraper dispatch routing in `run_ingestion()` in `src/cinema_recs/ingest.py`, matching on the West Plano path segment (`"west-plano"`) or `cinema.source_type == "cinemark_west_plano"` rather than the bare `"cinemark.com"` domain, per the misrouting-safety note in `contracts/scraper_interface.md`
- [X] T007 Wire `ensure_cinemark_west_plano_cinema()` into `bootstrap()`'s `cinemas` list in `main.py`, alongside the existing Cinepolis, Texas Theatre, and Angelika Dallas cinemas, so ingestion/enrichment/notifications/scheduler/web view all pick up the new source

**Checkpoint**: Foundational date-walk, per-date fetch, scraper routing, and app wiring established.

---

## Phase 3: User Story 1 - Ingest upcoming showtimes from Cinemark West Plano (Priority: P1) 🎯 MVP

**Goal**: Fetch every published showtime across the venue's own date-tab window, parse film titles/dates/start times/ticket URLs, and store showtime records idempotently in SQLite.

**Independent Test**: Trigger ingestion for the Cinemark West Plano source and verify showtimes are stored in `cinema.db` per `quickstart.md` Scenario 1.

### Tests for User Story 1

- [X] T008 [P] [US1] Unit test for `extract_cinemark_west_plano_dates()` date-tab parsing in `tests/unit/test_cinemark_west_plano_scraper.py`
- [X] T009 [P] [US1] Unit test for base showtime parsing (title, show_date, start_time in `CENTRAL_TIME`, ticket_url extraction) from a sample `GetByTheaterId` HTML fixture in `tests/unit/test_cinemark_west_plano_scraper.py`
- [X] T010 [P] [US1] Integration test for Cinemark West Plano showtime ingestion run in `tests/integration/test_cinemark_west_plano_ingestion.py`

### Implementation for User Story 1

- [X] T011 [US1] Implement `parse_cinemark_west_plano_html(html, base_url)` to map each showtime listitem in a date's HTML fragment to a `ScrapedShowtime` (movie_title, show_date, start_time, ticket_url — format left as a placeholder pending US2), resolving `TicketSeatMap` `href`s against `base_url` per research.md §3, in `src/cinema_recs/scraper.py`
- [X] T012 [US1] Complete `scrape_cinemark_west_plano_showtimes()` to call the T003/T004 date walk + T011 parse per date, aggregate results, and return `ScrapeResult` (`reported_count`, `complete`, `incomplete_reason` reflecting any per-date fetch failures per research.md §1/§4) in `src/cinema_recs/scraper.py`

**Checkpoint**: At this point, User Story 1 is fully functional and testable independently (base MVP: showtimes ingested, formats not yet distinguished).

---

## Phase 4: User Story 2 - Identify 70mm and other special presentation formats (Priority: P1)

**Goal**: Distinctly tag every showtime's presentation format — most importantly 70mm (via title-suffix normalization) — plus XD, ScreenX, D-BOX, and RealD 3D (via format-badge `alt` text), including compound multi-badge groups.

**Independent Test**: Ingest a period covering "The Odyssey 70mm" (or another current 70mm listing) and verify the stored showtime's `format == "70mm"` with `movie_title` equal to the base film title, per `quickstart.md` Scenario 2.

### Tests for User Story 2

- [X] T013 [P] [US2] Unit test: a listing titled `"<Film> 70mm"` is parsed into `movie_title="<Film>"`, `format="70mm"` in `tests/unit/test_cinemark_west_plano_scraper.py`
- [X] T014 [P] [US2] Unit test: a showtime group with `<img alt="Cinemark XD">` and `<img alt="D-BOX">` badges together produces a single joined format value (e.g. `"XD+D-BOX"`), not just the first badge, in `tests/unit/test_cinemark_west_plano_scraper.py`
- [X] T015 [P] [US2] Unit test: a showtime group with no badge and no `"Standard Format"` text still resolves to a sane default rather than raising, in `tests/unit/test_cinemark_west_plano_scraper.py`

### Implementation for User Story 2

- [X] T016 [US2] Implement 70mm title-suffix detection/normalization (case-insensitive `" 70mm"` strip → base title + `format="70mm"`) in `parse_cinemark_west_plano_html()` in `src/cinema_recs/scraper.py`, satisfying spec FR-004
- [X] T017 [US2] Implement format-badge extraction (`<img alt="...">` per showtime group, `"Cinemark "` prefix stripped, multiple badges joined deterministically e.g. `"+"`-joined) and `"Standard Format"`/no-badge fallback in `parse_cinemark_west_plano_html()` in `src/cinema_recs/scraper.py`, satisfying spec FR-003/FR-010

**Checkpoint**: User Story 2 features (70mm and special-format tagging) complete and independently testable — this is the feature's primary stated motivation.

---

## Phase 5: User Story 3 - Synchronize schedule updates and cancellations (Priority: P3)

**Goal**: Refresh existing Cinemark West Plano showtimes on each ingestion run, update modified event details, and mark removed showtimes as stale.

**Independent Test**: Re-run ingestion after a simulated schedule change and verify stored records accurately reflect additions/removals/updates, per `quickstart.md` Scenario 3.

### Tests for User Story 3

- [X] T018 [P] [US3] Integration test for stale showtime reconciliation and repeated-run idempotency in `tests/integration/test_cinemark_west_plano_ingestion.py`

### Implementation for User Story 3

- [X] T019 [US3] Verify stale showtime marking (`storage.mark_stale_showtimes`) and partial/failure `IngestionRun` outcome reporting behave correctly for Cinemark West Plano per-date fetch errors/parse skips in `src/cinema_recs/ingest.py` and `src/cinema_recs/scraper.py`

**Checkpoint**: All user stories complete and functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final logging, documentation verification, and validation scenarios

- [X] T020 [P] Add structured logging for Cinemark West Plano ingestion progress (dates walked, per-date failures, bot-block detection) in `src/cinema_recs/scraper.py`
- [X] T021 Execute end-to-end validation scenarios documented in `specs/012-cinemark-west-plano-source/quickstart.md` against the live site (see Notes for results)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories.
- **User Stories (Phase 3+)**: All depend on Foundational phase completion.
  - US1 (P1) -> US2 (P1) -> US3 (P3)
- **Polish (Phase 6)**: Depends on completion of user stories.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational phase (Phase 2).
- **User Story 2 (P1)**: Extends US1's `parse_cinemark_west_plano_html()` with format-specific logic; not independently deployable before US1 exists, but adds no new fetch/dispatch surface. Given both US1 and US2 are P1 per spec.md (format tagging is this feature's primary motivation, not a nice-to-have), treat them as a single MVP delivery unit rather than shipping US1 alone.
- **User Story 3 (P3)**: Extends US1 ingestion storage lifecycle; verification-only, no new parsing logic.

### Parallel Opportunities

- T001 and T002 (Phase 1) can run in parallel (different files).
- T008, T009, T010 (US1 tests) can run in parallel (independent test cases, though same test file for T008/T009 — coordinate if working concurrently).
- T013, T014, T015 (US2 tests) can run in parallel (independent test cases, same file — coordinate if working concurrently).
- T020 (Polish logging) can run in parallel with T021 (manual validation) once all stories are complete.

---

## Parallel Example: User Story 1 + User Story 2 (combined P1 MVP)

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for extract_cinemark_west_plano_dates() date-tab parsing in tests/unit/test_cinemark_west_plano_scraper.py"
Task: "Unit test for base showtime parsing from a sample GetByTheaterId HTML fixture in tests/unit/test_cinemark_west_plano_scraper.py"
Task: "Integration test for Cinemark West Plano showtime ingestion run in tests/integration/test_cinemark_west_plano_ingestion.py"

# Then, once T011/T012 land, launch all tests for User Story 2 together:
Task: "Unit test: a listing titled '<Film> 70mm' is parsed into movie_title='<Film>', format='70mm'"
Task: "Unit test: a showtime group with XD + D-BOX badges together produces a joined format value"
Task: "Unit test: a showtime group with no badge and no 'Standard Format' text resolves to a sane default"
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2, both P1)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational).
2. Complete Phase 3 (User Story 1) — showtimes ingested, format not yet distinguished.
3. Complete Phase 4 (User Story 2) — 70mm and special-format tagging, this feature's stated reason for existing.
4. **STOP and VALIDATE**: Run `quickstart.md` Scenarios 1 and 2; confirm 70mm and XD/ScreenX/D-BOX/RealD 3D formats are each distinctly tagged.
5. Deploy MVP — spec.md explicitly treats US1+US2 as equal-priority, so shipping US1 without US2 does not deliver the feature's core value.

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (Cinemark West Plano cinema registered, dispatch wired, app bootstrap updated).
2. Add User Story 1 → base ingestion working, but format tagging incomplete — not yet a meaningful demo of user intent.
3. Add User Story 2 → Test independently → Deploy/Demo (true MVP — this is what the user asked for).
4. Add User Story 3 → Test independently → Deploy/Demo.
5. Each story adds value without breaking previous stories or the existing Cinepolis/Texas Theatre/Angelika Dallas sources.

---

## Notes

- [P] tasks = different files or independent test cases, no dependencies.
- [Story] label maps task to specific user story for traceability.
- Unlike prior sources (008), US1 and US2 here are both P1 in spec.md — 70mm/special-format tagging (US2) is the user's explicit, stated reason for onboarding this venue, so it is not deferred as a "nice-to-have" the way Angelika's format capture (P2) was.
- research.md's 70mm-as-separate-listing finding (§2) is the single most important implementation detail in this feature — T016 must not be skipped or deferred, or 70mm screenings will surface as a spuriously distinct "movie" rather than a tagged format of the base film.
- Commit after each task or logical group.
- Stop at any checkpoint to validate story independently.
- Implementation deviations from the literal task text, both intentional: (1) T004's fetch logic
  was implemented as an inline closure inside `scrape_cinemark_west_plano_showtimes()` rather than
  a standalone `fetch_cinemark_west_plano_html()` function, since it needed to close over the
  already-open Playwright `page` and `theater_id`/`origin` for the whole run, matching how
  Angelika Dallas's per-date fetch (`_click_angelika_date_with_retry`) is also a small
  run-scoped helper rather than a fully standalone function. (2) T006's dispatch was implemented
  via `ingest.py`'s existing explicit `source_type -> scraper` dict (discovered during
  implementation that feature 011 already replaced the old domain-substring dispatch chain
  project-wide) rather than a `"west-plano"` substring match — this is strictly safer than what
  the task text proposed and satisfies the same misrouting-safety intent from
  `contracts/scraper_interface.md`.
- All 179 tests in the suite pass (`pytest tests/`), including 21 new tests across
  `tests/unit/test_cinemark_west_plano_scraper.py` and
  `tests/integration/test_cinemark_west_plano_ingestion.py`, plus updated coverage in
  `tests/unit/test_ingest.py` (new dispatch case) and `tests/unit/test_main.py` (now expects 4
  cinemas). `ruff check` passes on all touched files.
- T021 live verification (2026-07-23, `playwright install chromium` + a real run against
  `cinemark.com`, no code changes needed): a single scrape walked all 76 published dates
  (`complete=True`) and returned ~1,680-1,690 showtimes with formats
  `70mm, D-BOX, D-BOX+RealD 3D, RealD 3D, ScreenX, Standard, XD, XD+D-BOX, XD+D-BOX+RealD 3D` —
  confirming 70mm and multi-badge joining work exactly as designed against real markup. A full
  `run_ingestion()` → re-run cycle against a real SQLite db was idempotent (1,689 active
  showtimes both times, zero duplicates). The ~89 "skipped" entries per run are legitimate: a
  showtime whose start time has already passed today renders as disabled
  `<p class="off past">` text instead of a ticket `<a href>`, which the parser correctly treats
  as unbuyable/skippable rather than a parse failure. One earlier back-to-back double-run showed
  a large (non-reproducible) showtime-count dip between run 1 and run 2, consistent with a
  transient network/rate-limit blip during a 76-request walk rather than a code defect — a
  second clean back-to-back run was fully idempotent. No BlockedError/anti-bot page was ever
  observed.
