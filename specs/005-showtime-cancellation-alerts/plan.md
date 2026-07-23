# Implementation Plan: Showtime Cancellation & Reschedule Alerts

**Branch**: `005-showtime-cancellation-alerts` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-showtime-cancellation-alerts/spec.md`

## Summary

Extend feature 004's notification pipeline so that when the specific
showtime referenced in a prior recommendation notification disappears
from the source (transitions `active` → `stale`, per feature 001's
existing lifecycle), the operator gets a follow-up Discord alert: a
"cancelled" alert if the movie has no other active upcoming showtime, or
a "rescheduled" alert (old time → new time) if it does. This is
evaluated in the same per-cycle notification step feature 004 already
runs, immediately after it. `NotificationRecord` is extended to persist
which specific showtime (by id) was referenced in a recommendation
notification and whether a cancellation/reschedule alert has already
been sent for that showtime's disappearance, so re-notification is
suppressed on later cycles (FR-004) without a second webhook call if it
already ran once.

## Technical Context

**Language/Version**: Python 3.11+ (matches features 001-004)

**Primary Dependencies**: None new — reuses feature 004's
`discord_client.send_notification` (`requests.post`) and feature 001's
existing `active`/`stale` showtime lifecycle; no new library added

**Storage**: SQLite, same `cinema_recs.db` file — extends the existing
`notification_record` table (additive columns) rather than adding a new
table

**Testing**: `pytest` with `unittest.mock.patch`, matching features
002-004

**Target Platform**: Same Linux Docker container as features 001-004, on
the operator's Unraid server

**Project Type**: Single project — extends the existing
`src/cinema_recs/` package; no new service or container

**Performance Goals**: At most one additional webhook call per movie
whose previously-notified showtime disappears in a given cycle — bounded
by the same low, "tens of movies" scale as feature 004; adds negligible
time to the existing cycle

**Constraints**: MUST NOT re-notify for the same showtime's disappearance
across multiple cycles (FR-004); MUST NOT send when notifications are
disabled or no webhook is configured (FR-008, reusing feature 004's
switch); a failed delivery MUST NOT mark the disappearance as already
alerted (FR-007), mirroring feature 004's FR-005 pattern exactly

**Scale/Scope**: Bounded by the number of distinct movies with an
`active` notification record whose referenced showtime disappears in a
given cycle — a strict subset of feature 004's already-small per-cycle
volume

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Python-First | All logic (disappearance detection, cancelled/rescheduled classification, message build, delivery) implemented in Python | PASS |
| II. Docker-Native Deployment | Extends the existing single Docker image; no new container/service | PASS |
| III. Unraid Runtime Compatibility | No new env vars, volumes, or ports — reuses feature 004's `DISCORD_WEBHOOK_URL`/`NOTIFICATIONS_ENABLED` | PASS |
| IV. Simplicity & Solo-Maintainer Ergonomics | Reuses feature 004's webhook client and enable/disable switch as-is; adds columns to the existing `notification_record` table instead of a new table; no new dependency | PASS |
| V. Observability for Self-Hosting | Cancelled/rescheduled outcomes logged per movie per cycle, same pattern as feature 004's sent/failed logging | PASS |

No violations identified; Complexity Tracking is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/005-showtime-cancellation-alerts/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── contracts/            # Phase 1 output (/speckit-plan command)
└── tasks.md               # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
└── cinema_recs/
    ├── models.py          # extend: NotificationRecord gains showtime-reference + disappearance-alert fields
    ├── storage.py          # extend: notification_record additive migration; helpers to record/query the referenced showtime and disappearance-alert state
    ├── notify.py            # extend: after existing recommendation-notification pass, evaluate disappearance of previously-notified showtimes; build cancelled/rescheduled message; deliver via existing discord_client
    └── scheduler.py           # no change — already calls run_notifications() once per cycle; new logic lives inside that same call

tests/
└── unit/
    └── test_notify.py     # extend: cancelled/rescheduled scenarios alongside existing recommendation-notification tests
```

**Structure Decision**: This feature extends feature 004's existing
files in place rather than adding new ones — `notify.py` already owns
"what happens to a previously-notified movie on this cycle," so
cancellation/reschedule detection is a second pass inside the same
module and the same `run_notifications()` entry point the scheduler
already calls, not a new file or a new scheduled job. `discord_client.py`
is reused unchanged (it's already a generic "send this text" wrapper).
`scheduler.py` needs no edit since `run_notifications()` is already
wired into the per-cycle job.

## Complexity Tracking

*No violations — table intentionally omitted.*
