---

description: "Task list for Movie Metadata Enrichment via TMDB"

---

# Tasks: Movie Metadata Enrichment via TMDB

**Input**: Design documents from `/specs/002-tmdb-metadata-enrichment/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/movie-metadata-interface.md, quickstart.md

**Tests**: Lightweight unit/integration tests are included, consistent with feature 001's precedent and the constitution's guidance to test logic with real failure risk (TMDB matching, caching). Not a strict TDD gate.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Extends feature 001's existing single project: `src/cinema_recs/`, `tests/`, `main.py`, `requirements.txt` at repository root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add this feature's new dependency and configuration surface

- [X] T001 Add `requests` to `requirements.txt`
- [X] T002 [P] Add `TMDB_API_KEY` (required) to the config loader in `src/cinema_recs/config.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema and models that MUST exist before any user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Extend the SQLite schema in `src/cinema_recs/storage.py` with `movie_metadata` and `enrichment_attempt` tables (per data-model.md), added to the existing `init_schema()`
- [X] T004 [P] Add `MovieMetadata` and `EnrichmentAttempt` dataclasses to `src/cinema_recs/models.py` (per data-model.md)
- [X] T005 Implement `get_movie_metadata(db_path, movie_title)`, an upsert helper for `MovieMetadata`, and `record_enrichment_attempt(...)` in `src/cinema_recs/storage.py` (depends on T003, T004) — per contracts/movie-metadata-interface.md's return-value contract

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - Enrich ingested movies with metadata (Priority: P1) 🎯 MVP

**Goal**: Every distinct ingested movie title gets looked up against TMDB once and cached.

**Independent Test**: Ingest a showtime for a known movie title, run enrichment, and confirm a `MovieMetadata` row (genre, overview, release year, rating, runtime, poster) is stored; run enrichment again and confirm no repeat TMDB call for the same title.

### Tests for User Story 1

- [X] T006 [P] [US1] Unit test for TMDB search/detail client calls (mocked via `unittest.mock.patch`) in `tests/unit/test_tmdb_client.py`
- [X] T007 [P] [US1] Unit test for enrichment orchestration caching behavior (no re-lookup for already-enriched titles) in `tests/unit/test_enrich.py`

### Implementation for User Story 1

- [X] T008 [US1] Implement `search_movie(title)` and `get_movie_details(tmdb_id)` against TMDB's REST API, with fixed-delay pacing between calls, in `src/cinema_recs/tmdb_client.py`
- [X] T009 [US1] Implement match-acceptance logic (normalized title equality / clearly-best top result, else no match) in `src/cinema_recs/tmdb_client.py` (depends on T008)
- [X] T010 [US1] Implement enrichment orchestration in `src/cinema_recs/enrich.py`: find distinct movie titles from `showtime` with no `movie_metadata` row yet, call the TMDB client, store the result via T005's storage helpers (depends on T005, T009)
- [X] T011 [US1] Wire a one-shot enrichment call into `main.py` alongside the existing one-shot ingestion call (depends on T010)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently (quickstart.md steps 1 and 3)

---

## Phase 4: User Story 2 - Handle movies TMDB can't confidently match (Priority: P2)

**Goal**: Movies with no confident TMDB match are recorded unmatched, never given fabricated metadata.

**Independent Test**: Ingest a showtime for a title with no TMDB result (or an ambiguous one), run enrichment, and confirm the movie is recorded unmatched with no metadata attached.

### Tests for User Story 2

- [X] T012 [P] [US2] Unit test for unmatched outcomes (no TMDB result; ambiguous top candidates) in `tests/unit/test_tmdb_client.py`

### Implementation for User Story 2

- [X] T013 [US2] Ensure `tmdb_client.py`'s match-acceptance logic (T009) explicitly rejects ambiguous top candidates rather than guessing, distinguishing "no result" from "ambiguous result" in its return value (depends on T009)
- [X] T014 [US2] Ensure `enrich.py` stores an explicit `unmatched` `MovieMetadata` row (not just skipping) so the listing view can distinguish "attempted but unmatched" from "not yet attempted" (depends on T010, T013)

**Checkpoint**: User Stories 1 AND 2 both work independently — no movie ever displays another movie's metadata

---

## Phase 5: User Story 3 - View enriched showtimes (Priority: P2)

**Goal**: The existing listing view shows genre, rating, and poster inline for matched movies.

**Independent Test**: Enrich a known movie, then confirm the listing view shows its genre, rating, and poster alongside the existing showtime fields; confirm an unmatched movie's showtime still renders normally.

### Tests for User Story 3

- [X] T015 [P] [US3] Extend `tests/integration/test_web_view.py` with cases for enriched-field display and the unmatched fallback

### Implementation for User Story 3

- [X] T016 [US3] Extend the listing template in `src/cinema_recs/web.py` to display genre, rating, and poster when a matched `MovieMetadata` row exists (depends on T005)
- [X] T017 [US3] Ensure showtimes for unmatched/not-yet-attempted movies continue rendering normally with no broken or missing section in `src/cinema_recs/web.py` (depends on T016)

**Checkpoint**: All three user stories independently functional — enrichment, unmatched-safety, and visible display all work

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T018 [P] Add unit tests for TMDB request pacing and retry-on-transient-failure behavior in `tests/unit/test_tmdb_client.py`
- [X] T019 [P] Update `README.md` with `TMDB_API_KEY` setup instructions
- [X] T020 Run full quickstart.md validation end-to-end against the live TMDB API and a running feature-001 deployment

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on Foundational completion; builds directly on US1's matching logic (T009) and orchestration (T010)
- **User Story 3 (Phase 5)**: Depends on Foundational completion (T005); independent of US2, though realistically tested alongside it
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories — the MVP
- **User Story 2 (P2)**: Builds on US1's matching/orchestration (T009, T010) but is independently testable via its own ambiguous/no-match fixtures
- **User Story 3 (P2)**: Independent of US2 — only needs Foundational storage (T005); can be built in parallel with US2

### Parallel Opportunities

- T002 (Setup) can run in parallel with T001
- T004 (Foundational) can run in parallel with T003
- T006 and T007 (US1 tests) can run in parallel
- Once Foundational and US1 are done, US2 and US3 implementation can proceed in parallel (different files: `tmdb_client.py`/`enrich.py` vs `web.py`)

---

## Parallel Example: User Story 1

```bash
# Launch both User Story 1 tests together:
Task: "Unit test for TMDB search/detail client calls in tests/unit/test_tmdb_client.py"
Task: "Unit test for enrichment orchestration caching behavior in tests/unit/test_enrich.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Enrich a known movie, confirm metadata stored and cached on re-run
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Validate independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Validate unmatched-safety independently → Deploy/Demo
4. Add User Story 3 → Validate listing view independently → Deploy/Demo
5. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Feature 003 depends on this feature's `tmdb_id` (via `get_movie_metadata`, per contracts/movie-metadata-interface.md) — avoid changing that function's contract without checking feature 003's plan/tasks once they exist
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence

## Phase 7: Convergence

- [X] T021 Restore FR-007 compliance in `src/cinema_recs/web.py`'s `LISTING_TEMPLATE`: when a matched movie has no Letterboxd rating/link available (`section.letterboxd.get(s.movie_title)` is `None`, has no `letterboxd_slug`, or has `average_rating is none`), render the movie's stored `metadata.average_rating` (TMDB, plain text, unlinked) instead of "—", so the Rating column still displays a rating for every movie with stored TMDB metadata as FR-007 requires — while continuing to prefer the Letterboxd-linked rating when available per feature 010 FR-005 (contradicts FR-007)
