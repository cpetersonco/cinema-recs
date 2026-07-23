---

description: "Task list for Showtime Notifications"

---

# Tasks: Showtime Notifications

**Input**: Design documents from `/specs/004-showtime-notifications/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/notification-interface.md, quickstart.md

**Tests**: Lightweight unit tests are included, consistent with features 001-003's precedent and the constitution's guidance to test logic with real failure risk (notification dedup/state-transition tracking, webhook delivery resilience). Not a strict TDD gate.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Extends features 001-003's existing single project: `src/cinema_recs/`, `tests/`, `main.py`, `requirements.txt` at repository root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add this feature's new configuration surface (no new dependency — `requests` is already present from feature 002)

- [X] T001 Add `DISCORD_WEBHOOK_URL` (optional) and `NOTIFICATIONS_ENABLED` (optional, lenient-parsed boolean, default `true`) to the config loader in `src/cinema_recs/config.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema and models that MUST exist before any user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Extend the SQLite schema in `src/cinema_recs/storage.py` with a `notification_record` table (per data-model.md), added to the existing `init_schema()`
- [X] T003 [P] Add a `NotificationRecord` dataclass to `src/cinema_recs/models.py` (per data-model.md)
- [X] T004 Implement storage helpers in `src/cinema_recs/storage.py` (depends on T002, T003): `get_notification_record` / `upsert_notification_record`, and `get_next_showtime_for_movie(db_path, cinema_id, movie_title)` (earliest active showtime for a title, per research.md's "which showtime's date/time" decision)

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - Get notified when a showtime becomes recommended (Priority: P1) 🎯 MVP

**Goal**: The first time a movie becomes recommended, a Discord notification is sent with its title, next showtime, and matched reason(s).

**Independent Test**: Configure a feature-003 preference that matches a specific ingested/enriched movie, run recommendation evaluation followed by notification evaluation, and confirm a Discord notification is sent containing the movie title, date, start time, and matched reason(s).

### Tests for User Story 1

- [X] T005 [P] [US1] Unit test for `discord_client.send_notification` — successful `POST` records success, non-2xx/timeout/connection-error raises for the caller to handle (mocked via `unittest.mock.patch`) in `tests/unit/test_discord_client.py`
- [X] T006 [P] [US1] Unit test for `notify.py` orchestration — a newly-recommended movie triggers a notification whose message contains the movie title, next showtime date/time, matched reason(s), and (per FR-002a) that showtime's `ticket_url` when present; a showtime with `ticket_url = None` produces a message with no link (not a broken one); a non-recommended movie never triggers one; zero-config (no webhook URL, or `NOTIFICATIONS_ENABLED=false`) sends nothing and makes no webhook calls in `tests/unit/test_notify.py`

### Implementation for User Story 1

- [X] T007 [US1] Implement `send_notification(webhook_url, message)` — a thin `requests.post()` wrapper posting `{"content": message}` — in `src/cinema_recs/discord_client.py`
- [X] T008 [US1] Implement `run_notifications(db_path, cinema_id, config)` orchestration in `src/cinema_recs/notify.py`: short-circuit with zero webhook calls when no webhook URL is configured or notifications are disabled (FR-007); otherwise, for each matched movie's current recommendation, build the message (title, `get_next_showtime_for_movie`'s result's date/time and `ticket_url` per FR-002a — omit the link line entirely when `ticket_url` is `None`, don't render a placeholder — and `movie_recommendation.reasons`) and call `send_notification`, recording the outcome via `notification_record` (depends on T004, T007)
- [X] T009 [US1] Wire a one-shot notification evaluation call into `main.py` alongside the existing one-shot ingestion + enrichment + recommendation calls (depends on T008)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently (quickstart.md steps 1-2)

---

## Phase 4: User Story 2 - Avoid duplicate or noisy notifications (Priority: P2)

**Goal**: A movie that remains recommended across many showtimes/cycles is notified exactly once per continuous recommended span.

**Independent Test**: Have a movie's showtimes remain recommended across several ingestion/re-evaluation cycles and confirm only one notification is ever sent for that movie; confirm a failed delivery doesn't block a later retry; confirm a recommended→not-recommended→recommended cycle notifies again.

### Tests for User Story 2

- [X] T010 [P] [US2] Unit tests in `tests/unit/test_notify.py`: a movie that stays recommended across repeated `run_notifications` calls is notified only once (`notification_record.active` stays `true`, no second webhook call); a failed delivery leaves `active = false` so the next call retries; a movie that transitions recommended → not-recommended → recommended is notified again (not suppressed as a duplicate)

### Implementation for User Story 2

- [X] T011 [US2] Extend `notify.py`'s orchestration with `notification_record.active` state-transition tracking (research.md/data-model.md's enter/exit rule): skip movies whose current recommended span already notified successfully; reset `active = false` the moment a movie is observed no-longer-recommended; leave `active = false` on a failed delivery attempt so it's retried next cycle rather than silently dropped (depends on T008)

**Checkpoint**: User Stories 1 AND 2 both work independently — notifications fire once per recommended span, not once per cycle/showtime

---

## Phase 5: User Story 3 - Configure notification delivery (Priority: P3)

**Goal**: The operator can configure the webhook destination and turn notifications off entirely via env vars, with no rebuild/redeploy.

**Independent Test**: Configure a webhook URL and confirm notifications are delivered there; then set `NOTIFICATIONS_ENABLED=false` (restart) and confirm no further notifications are sent even when new recommended showtimes appear.

### Tests for User Story 3

- [X] T012 [P] [US3] Unit tests in `tests/unit/test_config.py` for `DISCORD_WEBHOOK_URL`/`NOTIFICATIONS_ENABLED` defaults (unset → disabled-by-absence / enabled-by-default) and lenient boolean parsing of `NOTIFICATIONS_ENABLED`

### Implementation for User Story 3

- [X] T013 [US3] Add dedicated tests in `tests/unit/test_notify.py` confirming `run_notifications` sends zero notifications and makes zero webhook calls when `DISCORD_WEBHOOK_URL` is unset, and separately when `NOTIFICATIONS_ENABLED=false` with a URL configured (exercises T008's gate from FR-006/FR-007 explicitly, rather than relying on US1's tests alone) (depends on T008)

**Checkpoint**: All three user stories independently functional — notification, dedup, and delivery configuration all work

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T014 [P] Extend `scheduler.py`'s periodic job to also run notification evaluation each cycle, alongside the existing enrichment + recommendation evaluation steps (per the spec's Assumptions: notifications run as part of the existing cycle, not a separate schedule)
- [X] T015 [P] Update `README.md` with `DISCORD_WEBHOOK_URL`/`NOTIFICATIONS_ENABLED` setup instructions
- [X] T016 Run full quickstart.md validation end-to-end against a real Discord webhook and a running features-001/002/003 deployment

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on Foundational completion; builds directly on US1's orchestration (T008)
- **User Story 3 (Phase 5)**: Depends on Foundational completion; adds dedicated coverage of a gate already present in US1's T008, so it can be built in parallel with US2
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories — the MVP
- **User Story 2 (P2)**: Builds on US1's orchestration (T008) — same function, extended with dedup state tracking, not new files
- **User Story 3 (P3)**: Builds on US1's orchestration (T008)'s existing gate — independent of US2, can proceed in parallel

### Parallel Opportunities

- T003 (Foundational) can run in parallel with T002
- T005 and T006 (US1 tests) can run in parallel
- Once US1's T008 is done, US2's T010/T011 and US3's T012/T013 can proceed in parallel (different test-case additions to the same files, but no code-path conflicts)
- T014 and T015 (Polish) can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch both User Story 1 tests together:
Task: "Unit test for discord_client.send_notification in tests/unit/test_discord_client.py"
Task: "Unit test for notify.py orchestration in tests/unit/test_notify.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Trigger a real recommendation, confirm a Discord message arrives with the right content
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Validate independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Validate no-duplicate-notifications independently → Deploy/Demo
4. Add User Story 3 → Validate delivery configuration independently → Deploy/Demo
5. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- This feature has no known downstream dependents (unlike features 002/003, which feed feature 003/004 respectively) — it is the last feature in the 001→002→003→004 chain per the spec's Dependencies section
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
