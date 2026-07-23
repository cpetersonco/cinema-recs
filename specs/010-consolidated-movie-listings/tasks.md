# Tasks: Consolidated Movie Listings with Ticket and Letterboxd Links

**Input**: Design documents from `/specs/010-consolidated-movie-listings/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/web-view.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. Per research.md, no schema change and no new dependencies are needed, so there is no Setup or Foundational phase — every story is independently buildable directly on today's code.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: User Story 1 - See each movie once per venue instead of once per showing (Priority: P1) 🎯 MVP

**Goal**: The listing page (`GET /`) shows at most one row per (movie, venue) pair, representing that movie's earliest upcoming active showtime at that venue, instead of one row per individual showing.

**Independent Test**: Ingest several active showtimes for the same movie at the same venue (different dates/times) and confirm `GET /` renders exactly one row for that movie under that venue's section.

### Tests for User Story 1

- [X] T001 [P] [US1] Integration test: multiple active showtimes for the same movie at the same venue render as exactly one row on `GET /`, in `tests/integration/test_web_view.py`
- [X] T002 [P] [US1] Integration test: the same movie active at two different venues renders one row under *each* venue's section (two rows total, not merged into one), in `tests/integration/test_web_view.py` — add a `second_cinema` fixture and build its own `create_app(config, [cinema, second_cinema])` client for this test

### Implementation for User Story 1

- [X] T003 [US1] Add a `_group_by_earliest_showtime_per_movie(showtimes: list[Showtime]) -> list[Showtime]` helper function in `src/cinema_recs/web.py` that returns one `Showtime` per distinct `movie_title`, keeping the first occurrence encountered — correct because `storage.list_active_showtimes` already orders by `show_date, start_time` (research.md §1), so the first showtime seen per movie is that movie's earliest upcoming one, matching `storage.get_next_showtime_for_movie`'s semantics with no extra query
- [X] T004 [US1] In `listing()` in `src/cinema_recs/web.py`, apply `_group_by_earliest_showtime_per_movie` to each cinema's `showtimes` list before it's stored in `cinema_sections` and passed to `LISTING_TEMPLATE` (the existing `distinct_titles`/`metadata`/`recommendations` dict-building already works unchanged against the now-deduplicated list)

**Checkpoint**: At this point, User Story 1 is fully functional and testable independently — the listing page shows one row per movie per venue (MVP ready)

---

## Phase 2: User Story 2 - Get to the ticket page directly from the listing (Priority: P2)

**Goal**: Each row on the listing page shows a link to the ticket-purchase page for the showtime it represents, when the source provided one.

**Independent Test**: Ingest a showtime with a captured ticket-purchase link and confirm that link appears on the movie's row and points to the same URL captured from the source.

### Tests for User Story 2

- [X] T005 [P] [US2] Integration test: a showtime with a `ticket_url` renders a link on its row pointing to that exact URL, in `tests/integration/test_web_view.py`
- [X] T006 [P] [US2] Integration test: a showtime with no `ticket_url` renders "—" on its row, not an empty or broken link, in `tests/integration/test_web_view.py`

### Implementation for User Story 2

- [X] T007 [US2] Add a "Tickets" column to `LISTING_TEMPLATE` in `src/cinema_recs/web.py` (new `<th>` in the header row and a matching `<td>` per row) rendering `<a href="{{ s.ticket_url }}">Buy tickets</a>` when `s.ticket_url` is truthy, else "—"

**Checkpoint**: User Stories 1 AND 2 both work independently — consolidated rows now include a working ticket link where available

---

## Phase 3: User Story 3 - Jump straight to Letterboxd from the rating (Priority: P2)

**Goal**: The rating shown on each row links to that movie's Letterboxd page, using the app's existing Letterboxd rating/slug data rather than the TMDB rating previously shown.

**Independent Test**: Ingest a movie with a resolved Letterboxd rating and confirm the rating displayed on its row links to that movie's Letterboxd page.

### Tests for User Story 3

- [X] T008 [P] [US3] Update `test_listing_shows_enriched_fields_for_matched_movie` in `tests/integration/test_web_view.py`: keep its genre/poster assertions (unchanged, still sourced from `MovieMetadata`), remove the `b"7.5"` (TMDB rating) assertion since the Rating column no longer shows TMDB's figure, and seed Letterboxd data via `storage.upsert_letterboxd_movie_data` so the test can assert the Letterboxd rating/link instead (data-model.md's column-source table)
- [X] T009 [P] [US3] Integration test: a movie with resolved `letterboxd_slug` and `average_rating` (via `storage.upsert_letterboxd_movie_data`) renders its rating as a link to `https://letterboxd.com/film/<slug>/`, in `tests/integration/test_web_view.py`
- [X] T010 [P] [US3] Integration test: a movie that is TMDB-matched but has no Letterboxd data yet (no `upsert_letterboxd_movie_data` call) renders "—" for Rating, not a broken link, in `tests/integration/test_web_view.py`
- [X] T011 [P] [US3] Integration test: a movie with a resolved `letterboxd_slug` but `average_rating=None` (slug resolved, rating fetch failed/pending — research.md §3) renders "—" for Rating, not a link with no number, in `tests/integration/test_web_view.py`

### Implementation for User Story 3

- [X] T012 [US3] Import `get_letterboxd_movie_data` from `cinema_recs.storage` in `src/cinema_recs/web.py`
- [X] T013 [US3] In `listing()` in `src/cinema_recs/web.py`, add a `"letterboxd": {title: get_letterboxd_movie_data(config.db_path, title) for title in distinct_titles}` entry to each cinema section dict, alongside the existing `metadata`/`recommendations` entries
- [X] T014 [US3] In `LISTING_TEMPLATE` in `src/cinema_recs/web.py`, change the Rating cell: look up `section.letterboxd.get(s.movie_title)`, and when both `letterboxd_slug` and `average_rating` are present render `<a href="{{ letterboxd_base_url }}/{{ lb.letterboxd_slug }}/">{{ lb.average_rating }}</a>`, otherwise render "—" — replacing the current `metadata.average_rating` (TMDB) display in that cell; Genre/Poster cells still read from `metadata` unchanged (each now wrapped in its own matched-status conditional, since the Rating cell in between no longer shares that conditional)

**Checkpoint**: All user stories are independently functional — consolidated rows now show a ticket link and a Letterboxd-linked rating

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Validate the complete feature end-to-end

- [X] T015 Run `quickstart.md`'s full validation sequence (steps 1-5) against a locally-run app — verified via a direct test-client smoke run: 3 showtimes for one movie collapsed to 1 row showing the earliest (Aug 1) date, with a working ticket link and a Letterboxd-linked rating (4.5) distinct from the stored TMDB rating (8.1); Recommended/genre/poster all rendered correctly on the same consolidated row
- [X] T016 [P] Review the full `tests/integration/test_web_view.py` suite (including tests unrelated to this feature, e.g. `/health` tests) still passes after the template changes, confirming no unintended regressions from the shared `LISTING_TEMPLATE` edits — full suite run: 152/152 tests pass across the whole project (20/20 in test_web_view.py)

---

## Dependencies & Execution Order

### Phase Dependencies

- **User Story 1 (Phase 1)**: No dependencies — can start immediately; delivers the MVP (consolidated rows)
- **User Story 2 (Phase 2)**: No dependency on User Story 1's grouping logic (a ticket link works whether rows are consolidated or not, per spec's independent-test framing) — but shares `LISTING_TEMPLATE` in the same file, so implement sequentially with Phase 1/3, not concurrently, to avoid template-edit conflicts
- **User Story 3 (Phase 3)**: Same as User Story 2 — independently testable, but shares `LISTING_TEMPLATE`/`listing()` with the other two stories in the same file
- **Polish (Phase 4)**: Depends on all three stories being complete

### Within Each User Story

- Tests before implementation (write and confirm failing first)
- Story complete before moving to next priority

### Parallel Opportunities

- T001 and T002 (US1 tests) can run in parallel — independent test functions
- T005 and T006 (US2 tests) can run in parallel
- T008-T011 (US3 tests) can run in parallel
- Implementation tasks (T003-T004, T007, T012-T014) all touch `src/cinema_recs/web.py` and are NOT parallelizable with each other — implement User Story 1's, then 2's, then 3's changes in sequence even though the stories are independently testable

---

## Parallel Example: User Story 1

```bash
# Launch both User Story 1 tests together:
Task: "Integration test: same movie, same venue, multiple showtimes -> one row in tests/integration/test_web_view.py"
Task: "Integration test: same movie at two venues -> one row per venue in tests/integration/test_web_view.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: User Story 1 (T001-T004)
2. **STOP and VALIDATE**: Run quickstart.md steps 1-2 independently — confirms consolidation alone already fixes the "wall of duplicate rows" problem
3. Deploy/demo if ready

### Incremental Delivery

1. Add User Story 1 → validate via quickstart steps 1-2 (MVP!)
2. Add User Story 2 → validate via quickstart step 3 (ticket link)
3. Add User Story 3 → validate via quickstart step 4 (Letterboxd rating link)
4. Each story adds value without breaking previous stories — all three ultimately land in the same `LISTING_TEMPLATE`/`listing()` edit, so implement and commit them in this order rather than interleaving

---

## Notes

- [P] tasks = different/independent test functions, no dependencies
- [Story] label maps task to specific user story for traceability
- All implementation tasks land in `src/cinema_recs/web.py` (Constitution IV — no new modules for a presentation-only change); the [P] markers apply only to the test tasks within each story, not across implementation tasks
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- After implementation, run `graphify update .` per the `after_implement` hook in `.specify/extensions.yml` (dispatched automatically by `/speckit-implement`)
