---

description: "Task list for Letterboxd Official Lists as Recommendation Filters"
---

# Tasks: Letterboxd Official Lists as Recommendation Filters

**Input**: Design documents from `/specs/013-letterboxd-official-lists/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/best-of-list-interface.md, quickstart.md

**Tests**: Included — feature 003's existing test suite already covers this code path (`tests/unit/test_letterboxd_client.py`, `tests/unit/test_recommend.py`, `tests/integration/test_web_view.py`) and the constitution's Network-Isolated Automated Tests principle expects new logic in these files to be covered the same way.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project (existing repo layout): `src/cinema_recs/`, `tests/unit/`, `tests/integration/` at repository root.

---

## Phase 1: Setup

**Purpose**: None required — this feature adds no new dependencies, files, tooling, or project structure (plan.md: "no new modules or directories"). Skipping straight to Foundational.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Introduce the `BestOfList` structure (display name + URL) and switch `recommend.py` to build reasons from display names instead of raw keys. Every user story depends on this mechanism existing before any list — old or new — can produce a human-readable reason.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T001 Define a `BestOfList` structure (`display_name: str`, `url: str`) in `src/cinema_recs/letterboxd_client.py`, and change `BUILT_IN_BEST_OF_LISTS` from `dict[str, str]` to `dict[str, BestOfList]`, giving the existing `official_top_250` entry `display_name="Official Top 250 Narrative Feature Films"` (its URL is unchanged)
- [X] T002 Update `src/cinema_recs/recommend.py`: `_refresh_reference_lists` must read `.url` off each `BUILT_IN_BEST_OF_LISTS` entry when calling `fetch_best_of_list_slugs`; `run_recommendation_evaluation` must append the entry's `.display_name` to `reasons` instead of `f"best_of:{list_key}"` (depends on T001)
- [X] T003 Update the existing assertion in `tests/unit/test_recommend.py::test_movie_on_best_of_list_is_recommended` from `assert "best_of:official_top_250" in rec.reasons` to `assert "Official Top 250 Narrative Feature Films" in rec.reasons` (depends on T002)

**Checkpoint**: `pytest tests/unit/test_recommend.py tests/unit/test_letterboxd_client.py` passes with the existing single list, now producing a human-readable reason. Foundation ready for onboarding additional lists.

---

## Phase 3: User Story 1 - See why a showtime matched a curated list (Priority: P1) 🎯 MVP

**Goal**: A movie on any of the 8 newly onboarded official Letterboxd lists is marked recommended, with the specific list name(s) it matched shown in `reasons`.

**Independent Test**: Seed a showtime whose movie is on one newly onboarded list only, run `run_recommendation_evaluation`, and confirm the showtime is recommended with that list's display name in `reasons`.

### Implementation for User Story 1

- [X] T004 [US1] Add the 8 new entries to `BUILT_IN_BEST_OF_LISTS` in `src/cinema_recs/letterboxd_client.py` per data-model.md's table (all under `letterboxd.com/official/list/...`, live-verified in research.md):
  - `top_500` → `BestOfList("Letterboxd's Top 500 Films", "https://letterboxd.com/official/list/letterboxds-top-500-films/")`
  - `most_fans` → `BestOfList("Top 250 Films with the Most Fans", "https://letterboxd.com/official/list/top-250-films-with-the-most-fans/")`
  - `top_250_animated` → `BestOfList("Top 250 Animated Films", "https://letterboxd.com/official/list/top-250-animated-films/")`
  - `top_250_horror` → `BestOfList("Top 250 Horror Films", "https://letterboxd.com/official/list/top-250-horror-films/")`
  - `top_250_documentary` → `BestOfList("Top 250 Documentary Films", "https://letterboxd.com/official/list/top-250-documentary-films/")`
  - `top_250_women_directors` → `BestOfList("Top 250 Films by Women Directors", "https://letterboxd.com/official/list/top-250-films-by-women-directors/")`
  - `top_250_black_directors` → `BestOfList("Top 250 Films by Black Directors", "https://letterboxd.com/official/list/top-250-films-by-black-directors/")`
  - `top_100_underseen` → `BestOfList("Top 100 Underseen Films", "https://letterboxd.com/official/list/top-100-underseen-films/")`
- [X] T005 [P] [US1] Add a unit test in `tests/unit/test_letterboxd_client.py` (mirroring `test_fetch_best_of_list_slugs_scrapes_given_url`) calling `fetch_best_of_list_slugs` against `BUILT_IN_BEST_OF_LISTS["top_250_horror"].url` with a canned `data-target-link` fixture, confirming the unchanged scraper works against the new URL shape (depends on T004)
- [X] T006 [US1] Add a unit test in `tests/unit/test_recommend.py` (mirroring `test_movie_on_best_of_list_is_recommended`) asserting a movie whose slug appears only in the `top_250_horror` mocked fetch result is recommended with `"Top 250 Horror Films"` in `rec.reasons` — acceptance scenario 1 (depends on T004)
- [X] T007 [US1] Add a unit test in `tests/unit/test_recommend.py` asserting a movie whose slug appears in both `official_top_250` and `top_250_animated` mocked fetch results has both `"Official Top 250 Narrative Feature Films"` and `"Top 250 Animated Films"` present in `rec.reasons` — acceptance scenario 2 (depends on T004; use a `fetch_best_of_list_slugs` side_effect keyed by URL so different lists return different slug sets, since the existing tests mock it as a single return value shared by every list)
- [X] T008 [US1] Add a unit test in `tests/unit/test_recommend.py` asserting a movie whose slug appears in none of the mocked best-of-list results and matches no other criterion is not recommended (`is_recommended is False`, `reasons is None`) — acceptance scenario 3 (depends on T004)

**Checkpoint**: User Story 1 is fully functional and testable independently — `pytest tests/unit/test_letterboxd_client.py tests/unit/test_recommend.py` passes with all 9 lists onboarded.

---

## Phase 4: User Story 2 - Lists stay current without a redeploy (Priority: P2)

**Goal**: Every onboarded list's cached membership refreshes each cycle; one list's fetch failure never wipes its cache or blocks the other 8 lists.

**Independent Test**: Run `_refresh_reference_lists` with one list's fetch raising and the others succeeding; confirm the failing list's previously cached slugs are retained and the others are updated.

### Implementation for User Story 2

- [X] T009 [US2] Add a unit test in `tests/unit/test_recommend.py` that seeds `letterboxd_reference_list` cache rows for two `best_of:*` keys via `storage.replace_reference_list_slugs`, then calls `_refresh_reference_lists` with `fetch_best_of_list_slugs` mocked via `side_effect` to raise for one list's URL and return a new slug set for another; assert (via `storage.get_reference_list_slugs`) the failing list's original cached slugs are unchanged and the succeeding list's cache reflects the new slugs (depends on T004; covers acceptance scenarios 1 and 2)
- [X] T010 [US2] In the same test, assert (via `caplog`) that a `Failed to refresh Letterboxd best-of list` warning is logged for the failing list's key only, and no such warning appears for the succeeding list's key

**Checkpoint**: User Stories 1 AND 2 both work independently — refresh resilience across all 9 lists is verified without any scheduler or config change.

---

## Phase 5: User Story 3 - Distinguish lists from each other in the UI (Priority: P3)

**Goal**: The showtime web listing shows the specific matched list name(s), not a raw key, for any best-of-list-based recommendation.

**Independent Test**: View the web listing for a showtime recommended via two different onboarded lists and confirm both display names appear in the rendered reason text.

### Implementation for User Story 3

- [X] T011 [US3] Add an integration test in `tests/integration/test_web_view.py` (extending `test_listing_shows_recommended_badge_and_reasons`'s pattern) that seeds a recommendation via `storage.upsert_movie_recommendation(..., reasons="Top 250 Horror Films,Top 250 Animated Films")` and asserts both display names appear verbatim in the rendered `GET /` response body

**Checkpoint**: All three user stories are independently functional. No `web.py` code change is needed for this story — T002 (Foundational) already makes `reasons` carry display names, so `web.py`'s existing verbatim rendering (`{{ recommendation.reasons }}`) surfaces them automatically; this phase only adds the regression test proving it.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and final validation across all stories

- [X] T012 [P] Update `README.md`'s "built-in best-of list" reference (singular, near the top) to reflect that recommendations now check against 9 built-in Letterboxd official lists, not one
- [X] T013 Run `specs/013-letterboxd-official-lists/quickstart.md`'s validation steps (build, run, check refresh logs for 9 `Refreshed best-of list` lines, view `/` for display-name reasons, confirm multi-list reasons) against a local Docker build
- [X] T014 Run the full test suite (`pytest`) to confirm no regressions in `tests/unit/test_notify.py` or other consumers of `movie_recommendation.reasons`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Skipped — no tasks
- **Foundational (Phase 2)**: T001 → T002 → T003, strictly sequential (same two files) — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational. T004 first (data), then T005-T008 depend on T004 but are otherwise independent of each other
- **User Story 2 (Phase 4)**: Depends on Foundational + T004 (needs at least 2 lists to test isolation across lists); independent of US1's test tasks
- **User Story 3 (Phase 5)**: Depends on Foundational only (T002's reason-format change is what US3 verifies); does not require T004, though testing with real onboarded list names (as T011 does) is more representative
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories
- **User Story 2 (P2)**: Independently testable; shares T004's list entries with US1 but adds no new production code
- **User Story 3 (P3)**: Independently testable; adds no new production code beyond Foundational

### Within Each User Story

- T004 (data) before any test task that references the new list keys (T005-T009)
- Test tasks within a story are otherwise parallelizable (different test functions, same file — see note below)

### Parallel Opportunities

- T001-T003 are sequential (same two files, each depends on the previous)
- T005 can run in parallel with T006-T008 (different test files: `test_letterboxd_client.py` vs `test_recommend.py`)
- T006, T007, T008 all edit `tests/unit/test_recommend.py` — not marked `[P]` despite being logically independent, to avoid merge conflicts editing the same file; implement sequentially or coordinate carefully if parallelizing
- T012 (README) can run in parallel with any other Phase 6 task, or with any user-story phase once Foundational is done

---

## Parallel Example: User Story 1

```bash
# T004 must complete first (adds the list entries T005-T008 test against).
# Once T004 is done, these can run in parallel (different files):
Task: "Add unit test in tests/unit/test_letterboxd_client.py for fetch_best_of_list_slugs against a new list URL"
Task: "Add unit tests in tests/unit/test_recommend.py for single-list, multi-list, and no-list-match reasons"
```

---

## Implementation Strategy

### MVP First (Foundational + User Story 1 Only)

1. Complete Phase 2: Foundational (T001-T003) — reasons already read as display names, still just 1 list
2. Complete Phase 3: User Story 1 (T004-T008) — 9 lists onboarded, matching/reasons verified
3. **STOP and VALIDATE**: `pytest tests/unit/test_letterboxd_client.py tests/unit/test_recommend.py`, then run `specs/013-letterboxd-official-lists/quickstart.md` step 3
4. Deploy/demo if ready — this alone delivers the feature's core value (spec's User Story 1)

### Incremental Delivery

1. Foundational (T001-T003) → mechanism ready, no visible change yet (1 list, now with a real name)
2. Add User Story 1 (T004-T008) → 9 lists live, reasons name the specific list → **MVP**
3. Add User Story 2 (T009-T010) → refresh resilience across 9 lists verified by test
4. Add User Story 3 (T011) → web view display verified by test (already worked from Foundational; this closes the test gap)
5. Polish (T012-T014) → docs + full-suite regression check

---

## Notes

- No new dependencies, schema, routes, or env vars — every task touches one of `letterboxd_client.py`, `recommend.py`, `tests/unit/test_letterboxd_client.py`, `tests/unit/test_recommend.py`, `tests/integration/test_web_view.py`, or `README.md`.
- [P] tasks = different files, no dependencies.
- Commit after each task or logical group.
- Per Constitution Principle VIII, all new tests mock `fetch_best_of_list_slugs`/`fetch_watchlist_slugs`/`fetch_movie_rating` at the client-function boundary — none make real network calls.
- After implementation completes, the `after_implement` hook in `.specify/extensions.yml` (graphify) refreshes the knowledge graph automatically — no manual task needed for that.
