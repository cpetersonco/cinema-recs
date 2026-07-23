---

description: "Task list for Showtime Cancellation & Reschedule Alerts"

---

# Tasks: Showtime Cancellation & Reschedule Alerts

**Input**: Design documents from `/specs/005-showtime-cancellation-alerts/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/disappearance-alert-interface.md, quickstart.md

**Tests**: Lightweight unit tests are included, consistent with feature 004's precedent and the constitution's guidance to test logic with real failure risk (disappearance detection, cancelled/rescheduled classification, dedup/state tracking, webhook delivery resilience). Not a strict TDD gate.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Extends feature 004's existing single project: `src/cinema_recs/`, `tests/` at repository root. No new files are introduced — every task below edits an existing module.

---

## Phase 1: Foundational (Blocking Prerequisites)

**Purpose**: Extend the `notification_record` schema/model and storage helpers so a recommendation notification records which specific showtime it referenced — required by every user story below. No new configuration is introduced (this feature reuses feature 004's `DISCORD_WEBHOOK_URL`/`NOTIFICATIONS_ENABLED` as-is), so there is no separate Setup phase.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T001 [P] Extend the `NotificationRecord` dataclass in `src/cinema_recs/models.py` with `notified_showtime_id: Optional[int]` and `disappearance_alerted: bool` (per data-model.md)
- [X] T002 Extend the `notification_record` schema in `src/cinema_recs/storage.py`: add `notified_showtime_id INTEGER` and `disappearance_alerted INTEGER NOT NULL DEFAULT 0` to the `CREATE TABLE IF NOT EXISTS notification_record` statement, plus an additive `_migrate_add_notification_disappearance_columns(conn)` migration (mirroring the existing `_migrate_add_showtime_ticket_url` pattern at storage.py:128) wired into `init_schema()` so existing databases upgrade safely
- [X] T003 Extend `get_notification_record` and `upsert_notification_record` in `src/cinema_recs/storage.py` to read/write `notified_showtime_id` and `disappearance_alerted` (depends on T001, T002)
- [X] T004 [P] Add `get_showtime_by_id(db_path: str, showtime_id: int) -> Optional[Showtime]` in `src/cinema_recs/storage.py`, reusing the existing `_row_to_showtime` helper
- [X] T005 Update the existing recommendation-notification path in `src/cinema_recs/notify.py`'s `run_notifications` (the branch that already calls `storage.upsert_notification_record(..., active=True, ...)` on a successful send) to also pass `notified_showtime_id=showtime.id, disappearance_alerted=False`, and update the "movie dropped out of recommended" branch to also clear `notified_showtime_id=None, disappearance_alerted=False` (depends on T003; data-model.md State Transitions #1 and #5)

**Checkpoint**: Foundation ready — every new recommendation notification now records which showtime it referenced, and user story implementation can begin

---

## Phase 2: User Story 1 - Get notified when an already-alerted showing is cancelled (Priority: P1) 🎯 MVP

**Goal**: When a previously-notified showtime disappears from the source and the movie has no other active upcoming showtime, send a "cancelled" Discord alert identifying the movie and the original date/time.

**Independent Test**: Let a showtime be recommended and notified (feature 004), then remove it from a later ingestion run so it transitions to `stale` with no other active upcoming showtime for that movie, and confirm a "cancelled" Discord notification is sent referencing the original showing's date/time.

### Tests for User Story 1

- [X] T006 [P] [US1] Unit test in `tests/unit/test_notify.py`: a notification record with `active=True`, a `notified_showtime_id` whose `Showtime.status` is `stale`, and no other active showtime for that movie (`get_next_showtime_for_movie` returns `None`) produces a "cancelled" message containing the movie title and the original showing's date/time, and sets `disappearance_alerted=True` on success; a showtime that was never referenced by a notification record (no matching `notified_showtime_id`) never triggers this path

### Implementation for User Story 1

- [X] T007 [US1] Implement `_build_cancelled_message(movie_title: str, original_showtime) -> str` in `src/cinema_recs/notify.py`, following the existing `_build_message` style (spec FR-002)
- [X] T008 [US1] Implement a disappearance-evaluation pass (e.g. `_evaluate_disappearances(db_path, cinema_id, config)`) in `src/cinema_recs/notify.py`: iterate notification records with `active=True` and `notified_showtime_id is not None`; look up that showtime via `get_showtime_by_id` (T004); when its `status == 'stale'` and `get_next_showtime_for_movie` returns `None`, build the cancelled message (T007), send via the existing `discord_client.send_notification`, and on success call `upsert_notification_record(..., disappearance_alerted=True)` (depends on T004, T005, T007; research.md's disappearance-detection decision)
- [X] T009 [US1] Call the new disappearance-evaluation pass from `run_notifications()` immediately after the existing recommendation-notification loop, inside the same function (per plan.md's Structure Decision — one entry point, not a new scheduled job) (depends on T008)

**Checkpoint**: User Story 1 is fully functional and testable independently (quickstart.md step 2)

---

## Phase 3: User Story 2 - Get notified when an already-alerted showing is rescheduled (Priority: P1)

**Goal**: When a previously-notified showtime disappears but the movie still has another active upcoming showtime, send a "rescheduled" Discord alert with both the original and new date/time, and start tracking the new showtime for future disappearance checks.

**Independent Test**: Let a showtime be recommended and notified, then remove that specific showtime in a later ingestion run while a different active upcoming showtime for the same movie remains (or newly appears), and confirm a "rescheduled" Discord notification is sent with both the original and new date/time.

### Tests for User Story 2

- [X] T010 [P] [US2] Unit tests in `tests/unit/test_notify.py`: a notification record whose `notified_showtime_id` is `stale` and whose movie still has another active upcoming showtime (`get_next_showtime_for_movie` returns a `Showtime`) produces a "rescheduled" message containing the movie title, original date/time, and new date/time, and updates `notified_showtime_id` to the new showtime's id with `disappearance_alerted` reset to `False`; a movie that receives a reschedule alert and later has its *new* showtime also disappear with no further replacement produces a separate "cancelled" alert on a later evaluation (spec User Story 2 Acceptance Scenario 2)

### Implementation for User Story 2

- [X] T011 [US2] Implement `_build_rescheduled_message(movie_title: str, original_showtime, new_showtime) -> str` in `src/cinema_recs/notify.py` (spec FR-003)
- [X] T012 [US2] Extend the disappearance-evaluation pass (T008) with the reschedule branch: when `get_next_showtime_for_movie` returns a `Showtime` instead of `None`, build the rescheduled message (T011), send it, and on success call `upsert_notification_record(..., notified_showtime_id=new_showtime.id, disappearance_alerted=False)` so the new showtime is tracked for its own future disappearance (depends on T008, T011; data-model.md State Transition #3)

**Checkpoint**: User Stories 1 AND 2 both work independently — cancelled and rescheduled alerts both fire correctly, and a rescheduled showing can still later be cancelled (quickstart.md steps 2-4)

---

## Phase 4: User Story 3 - Avoid duplicate or noisy cancellation/reschedule alerts (Priority: P2)

**Goal**: At most one cancellation-or-reschedule notification is sent per disappearance event, and a failed delivery never blocks ingestion or gets silently dropped.

**Independent Test**: Let a notified showtime go stale, confirm one cancellation/reschedule alert fires, then run ingestion/evaluation several more times with the showtime still absent and confirm no repeat alert is sent; confirm a failed delivery is retried on a later cycle rather than lost.

### Tests for User Story 3

- [X] T013 [P] [US3] Unit tests in `tests/unit/test_notify.py`: (a) once `disappearance_alerted=True` for a showing, later evaluation passes make no further webhook call for it; (b) a failed cancelled/rescheduled delivery (mocked exception from `send_notification`) leaves `disappearance_alerted=False` (and, for the reschedule case, `notified_showtime_id` unchanged) so a later evaluation retries, and does not raise out of `run_notifications`; (c) with `NOTIFICATIONS_ENABLED=false` or no `DISCORD_WEBHOOK_URL` configured, the disappearance-evaluation pass makes zero webhook calls, reusing the same top-of-function gate as the existing recommendation-notification pass (spec FR-008)

### Implementation for User Story 3

- [X] T014 [US3] Extend the disappearance-evaluation pass (T008/T012) in `src/cinema_recs/notify.py` with: a skip guard for notification records where `disappearance_alerted` is already `True` for the current `notified_showtime_id` (spec FR-004); and a `try/except` around each delivery attempt that logs the failure and leaves state unchanged for retry, mirroring feature 004's `run_notifications` failure-handling for recommendation notifications (spec FR-007) (depends on T008, T012)

**Checkpoint**: All three user stories independently functional — cancellation, reschedule, and dedup/resilience all work (quickstart.md steps 2-6)

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect the whole feature

- [X] T015 [P] Update `README.md`'s existing notifications section to mention that a previously-notified showing's cancellation or reschedule also triggers a Discord alert, reusing the same `DISCORD_WEBHOOK_URL`/`NOTIFICATIONS_ENABLED` configuration (no new env vars)
- [X] T016 Run full quickstart.md validation end-to-end against a real Discord webhook and a running features-001/004 deployment (cancelled, rescheduled, reschedule-then-cancel, webhook-failure retry, and disable-switch scenarios)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 1)**: No dependencies — can start immediately; BLOCKS all user stories
- **User Story 1 (Phase 2)**: Depends on Foundational completion
- **User Story 2 (Phase 3)**: Depends on Foundational completion; extends US1's disappearance-evaluation pass (T008) with a second branch
- **User Story 3 (Phase 4)**: Depends on Foundational completion; extends the same pass (T008/T012) with dedup + failure-resilience guards, so it's built after US1/US2 but touches the same function
- **Polish (Phase 5)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories — the MVP (cancelled alerts)
- **User Story 2 (P1)**: Builds on US1's disappearance-evaluation pass (T008) — same function, extended with the reschedule branch, not new files
- **User Story 3 (P2)**: Builds on US1/US2's pass (T008/T012) — independent concern (idempotency + resilience) layered on top

### Parallel Opportunities

- T001 and T004 (Foundational) can run in parallel with T002
- T006 (US1 test) has no parallel sibling within its story, but can be written alongside T010/T013 once T008's shape is known
- T007 and T011 (message builders) can be implemented in parallel with each other once Foundational is done, since they don't share code
- T015 (Polish) can run in parallel with T016

---

## Parallel Example: Foundational Phase

```bash
# Launch independent foundational tasks together:
Task: "Extend NotificationRecord dataclass in src/cinema_recs/models.py"
Task: "Add get_showtime_by_id in src/cinema_recs/storage.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Foundational
2. Complete Phase 2: User Story 1 (cancelled alerts)
3. **STOP and VALIDATE**: Trigger a real showing disappearance with no replacement, confirm a "cancelled" Discord message arrives
4. Deploy/demo if ready

### Incremental Delivery

1. Complete Foundational → showtime-reference tracking ready
2. Add User Story 1 → Validate cancelled alerts independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Validate rescheduled alerts independently → Deploy/Demo
4. Add User Story 3 → Validate dedup + webhook-failure resilience independently → Deploy/Demo
5. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- This feature has a hard dependency on feature 004 (it only evaluates showtimes feature 004 already notified for) and, transitively, on feature 001's existing `active`/`stale` showtime lifecycle — it adds no new scraping or scheduling logic of its own (plan.md's Structure Decision)
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
