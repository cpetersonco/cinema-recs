---

description: "Task list for Showtime Recommendation Rules"

---

# Tasks: Showtime Recommendation Rules

**Input**: Design documents from `/specs/003-showtime-recommendation-rules/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/recommendation-interface.md, quickstart.md

**Tests**: Lightweight unit/integration tests are included, consistent with features 001/002's precedent and the constitution's guidance to test logic with real failure risk (Letterboxd matching/scraping, recommendation gating, resilient caching). Not a strict TDD gate.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Extends features 001/002's existing single project: `src/cinema_recs/`, `tests/`, `main.py`, `requirements.txt` at repository root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add this feature's new configuration surface (no new dependency — `requests` is already present from feature 002)

- [X] T001 Add `LETTERBOXD_USERNAME` (optional) and `LETTERBOXD_RATING_THRESHOLD` (optional, lenient-parsed per FR-008) to the config loader in `src/cinema_recs/config.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema and models that MUST exist before any user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Extend the SQLite schema in `src/cinema_recs/storage.py` with `letterboxd_movie_data`, `letterboxd_reference_list`, and `movie_recommendation` tables (per data-model.md), added to the existing `init_schema()`
- [X] T003 [P] Add `LetterboxdMovieData` and `MovieRecommendation` dataclasses to `src/cinema_recs/models.py` (per data-model.md)
- [X] T004 Implement storage helpers in `src/cinema_recs/storage.py` (depends on T002, T003): `get_letterboxd_movie_data` / `upsert_letterboxd_movie_data`, `get_reference_list_slugs` / `replace_reference_list_slugs` (replace-on-success-only, per data-model.md's resilience rule), `get_movie_recommendation` / `upsert_movie_recommendation`, and `list_distinct_matched_movie_titles_without_letterboxd_data` — per contracts/recommendation-interface.md's return-value contract

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - Get recommended showtimes based on Letterboxd signals (Priority: P1) 🎯 MVP

**Goal**: Every matched movie is evaluated against watchlist/rating/best-of-list criteria and marked recommended with matched reason(s) when at least one hits.

**Independent Test**: Configure a Letterboxd username with a known watchlist, ingest+enrich a showtime for a movie on that watchlist, run recommendation evaluation, and confirm it's marked recommended with `reasons` including `watchlist`, while a showtime for an unrelated movie is not.

### Tests for User Story 1

- [X] T005 [P] [US1] Unit test for Letterboxd client calls — TMDB-id-to-slug resolution, per-movie rating parse (JSON-LD), watchlist/list slug-page pagination scraping, request pacing, and retry-on-transient-failure (mocked via `unittest.mock.patch`) in `tests/unit/test_letterboxd_client.py`
- [X] T006 [P] [US1] Unit test for recommendation evaluation orchestration — per-criterion matching (watchlist/rating/best-of-list), the FR-005/SC-004 zero-config gate, caching of per-movie Letterboxd data (no re-fetch for already-cached movies), and resilience to a failed watchlist/list re-fetch (stale cache preserved, not treated as empty) in `tests/unit/test_recommend.py`

### Implementation for User Story 1

- [X] T007 [US1] Implement `resolve_letterboxd_slug(tmdb_id)` and `fetch_movie_rating(slug)` against Letterboxd's public pages, with fixed-delay pacing and retry between calls (mirroring `tmdb_client.py`), in `src/cinema_recs/letterboxd_client.py`
- [X] T008 [US1] Implement `fetch_watchlist_slugs(username)` and `fetch_best_of_list_slugs(list_url)`, paginating `.../page/{n}/` until the last page (per research.md), in `src/cinema_recs/letterboxd_client.py` (depends on T007)
- [X] T009 [US1] Define the built-in best-of list constant(s) (starting with `official_top_250` → `https://letterboxd.com/ctsearles/list/official-top-250-narrative-feature-films/`, per research.md) in `src/cinema_recs/letterboxd_client.py`
- [X] T010 [US1] Implement recommendation evaluation orchestration in `src/cinema_recs/recommend.py`: refresh watchlist/best-of-list reference caches (skip refresh and keep prior cache on fetch failure), fetch+cache Letterboxd data for any matched movie not yet cached, then compute and store each matched movie's recommendation status and matched reason(s) — applying the FR-005/SC-004 zero-config gate from research.md (depends on T004, T008, T009)
- [X] T011 [US1] Wire a one-shot recommendation evaluation call into `main.py` alongside the existing one-shot ingestion + enrichment calls (depends on T010)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently (quickstart.md steps 1, 3, 5)

---

## Phase 4: User Story 2 - See recommended showtimes at a glance (Priority: P2)

**Goal**: The existing listing view visually distinguishes recommended showtimes and shows why.

**Independent Test**: Ingest/enrich a movie that matches a configured preference, run recommendation evaluation, and confirm its showtime is visually marked recommended (with reasons) in the listing view, while non-matching showtimes render normally.

### Tests for User Story 2

- [X] T012 [P] [US2] Extend `tests/integration/test_web_view.py` with cases for the recommended badge/reasons display and the non-recommended fallback

### Implementation for User Story 2

- [X] T013 [US2] Extend the listing template in `src/cinema_recs/web.py` to show a recommended badge and matched reason(s) when a `MovieRecommendation` row has `is_recommended = True` (depends on T004)
- [X] T014 [US2] Ensure showtimes for non-recommended/not-yet-evaluated movies continue rendering normally with no broken or missing section in `src/cinema_recs/web.py` (depends on T013)

**Checkpoint**: User Stories 1 AND 2 both work independently — recommendations are visible and non-recommended rows stay intact

---

## Phase 5: User Story 3 - Update rating threshold and see recommendations change (Priority: P3)

**Goal**: Changing the rating threshold (env var + restart) or the operator's Letterboxd watchlist is reflected in recommendations on the next evaluation cycle, with no rebuild/redeploy.

**Independent Test**: Change the rating threshold, trigger recommendation evaluation again, and confirm previously recommended showtimes that only matched via rating and no longer meet the new threshold are unmarked, while newly matching ones are marked.

### Tests for User Story 3

- [X] T015 [P] [US3] Unit test in `tests/unit/test_recommend.py` asserting that re-running evaluation with a changed rating threshold un-marks a showtime that only matched via rating and no longer qualifies, and marks a newly-qualifying one

### Implementation for User Story 3

- [X] T016 [US3] Extend `src/cinema_recs/scheduler.py`'s periodic job to also run enrichment and recommendation evaluation each cycle (closes feature 002's scheduler gap; needed so FR-002/FR-007/SC-002's periodic re-evaluation happens without requiring a container restart between ingestion cycles) (depends on T010)

**Checkpoint**: All three user stories independently functional — evaluation, visibility, and reactive re-evaluation all work

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T017 [P] Update `README.md` with `LETTERBOXD_USERNAME`/`LETTERBOXD_RATING_THRESHOLD` setup instructions
- [X] T018 Run full quickstart.md validation end-to-end against the live Letterboxd site and a running features-001/002 deployment

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on Foundational completion (T004); independent of US1's Letterboxd-fetching internals, though realistically tested alongside it since it needs recommendation data to display
- **User Story 3 (Phase 5)**: Depends on User Story 1's orchestration (T010) — it extends *when* evaluation runs, not *how*
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories — the MVP
- **User Story 2 (P2)**: Only needs Foundational storage (T004) to read recommendation data; independent of US1's fetch/evaluate internals
- **User Story 3 (P3)**: Builds directly on US1's evaluation orchestration (T010) — it's the same logic run on a schedule, not new evaluation logic

### Parallel Opportunities

- T003 (Foundational) can run in parallel with T002
- T005 and T006 (US1 tests) can run in parallel
- Once Foundational is done, US2's implementation (T013/T014) can proceed in parallel with US1's Letterboxd-fetching work (T007-T010), since US2 only needs the `movie_recommendation` table shape (T004), not real data, to build/test its rendering logic against fixture rows

---

## Parallel Example: User Story 1

```bash
# Launch both User Story 1 tests together:
Task: "Unit test for Letterboxd client calls in tests/unit/test_letterboxd_client.py"
Task: "Unit test for recommendation evaluation orchestration in tests/unit/test_recommend.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Evaluate a known watchlist movie, confirm it's marked recommended with the right reason
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Validate independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Validate visibility independently → Deploy/Demo
4. Add User Story 3 → Validate reactive re-evaluation independently → Deploy/Demo
5. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Feature 004 depends on this feature's `movie_recommendation` data (via `storage.get_movie_recommendation`, per contracts/recommendation-interface.md) — avoid changing that function's contract without checking feature 004's plan/tasks
- This feature also extends `scheduler.py`'s periodic job (T016) to run feature 002's enrichment step — a gap left open by feature 002's own task scope — since this feature's periodic re-evaluation requirement can't be met otherwise
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
