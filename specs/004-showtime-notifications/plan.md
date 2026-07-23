# Implementation Plan: Showtime Notifications

**Branch**: `004-showtime-notifications` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-showtime-notifications/spec.md`

## Summary

Extend the existing cinema-recs pipeline (features 001-003) so that the
first time a movie becomes recommended (per feature 003's
watchlist/rating/best-of-list criteria), a Discord notification is sent
containing the movie title, its next active showtime's date/start time,
a direct ticket-purchase link when one is available (FR-002a, sourced
from feature 001's `Showtime.ticket_url`), and the specific matched
reason(s). Notifications are deduped per movie per continuous
recommended span (not per showtime, not per evaluation cycle) and are
resilient to webhook delivery failure — a failure is logged and retried
on the next cycle rather than silently dropped. Delivery destination and
an explicit enable/disable switch are both configured via environment
variables.

**Amendment (2026-07-22, `/speckit-clarify` session)**: Added FR-002a
(ticket link) plus explicit confirmation of two decisions already
reflected in the original research.md (earliest-upcoming-showtime
selection; `NOTIFICATIONS_ENABLED` defaulting to on once a webhook URL
is configured). FR-002a required no new data source — see research.md's
new decision section — since feature 001's `Showtime.ticket_url` (its
own FR-011, added in the same clarification session) is already returned
by this feature's planned `get_next_showtime_for_movie` helper.

## Technical Context

**Language/Version**: Python 3.11+ (matches features 001-003)

**Primary Dependencies**: `requests` (already present from feature 002)
— a Discord webhook is a single JSON `POST`, so no Discord SDK is added
(research.md)

**Storage**: SQLite — same database file features 001-003 already use
(`cinema_recs.db`), extended with one new table (`notification_record`)

**Testing**: `pytest` with `unittest.mock.patch` (stdlib), matching
features 002/003's approach — no new test dependency

**Target Platform**: Same Linux Docker container as features 001-003,
deployed on the operator's Unraid server

**Project Type**: Single project — extends the existing
`src/cinema_recs/` package and container rather than introducing a new
service

**Performance Goals**: Notification delivery is a single low-volume
webhook call per newly-recommended movie per cycle (bounded by the same
"tens of movies" scale as features 002/003); not latency-sensitive and
adds negligible time to the existing refresh cycle

**Constraints**: `DISCORD_WEBHOOK_URL` and `NOTIFICATIONS_ENABLED` are
both optional; with no URL configured, or with the flag explicitly
disabled, zero notifications must ever be sent (FR-007) without
attempting any webhook calls. A failed delivery MUST NOT mark a movie as
notified (FR-005)

**Scale/Scope**: At most one notification per distinct recommended movie
per cycle — bounded by the same "tens of movies" scale as feature
002/003's per-cycle work, typically far fewer since most movies won't be
newly-recommended most cycles

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Python-First | All logic (webhook client, dedup/state-transition tracking, storage) implemented in Python | PASS |
| II. Docker-Native Deployment | Extends the existing single Docker image; no new container/service | PASS |
| III. Unraid Runtime Compatibility | New config via env vars only; no new volume/port requirements beyond features 001-003's existing ones | PASS |
| IV. Simplicity & Solo-Maintainer Ergonomics | Plain `requests.post()`, no Discord SDK, no independent retry/backoff mechanism (next-cycle retry is sufficient per research.md), reuses the existing refresh-interval cycle rather than a separate notification schedule | PASS |
| V. Observability for Self-Hosting | Delivery outcomes (`sent`/`failed`) logged per movie per cycle, same pattern as ingestion/enrichment/recommendation-evaluation logging | PASS |

No violations identified; Complexity Tracking is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/004-showtime-notifications/
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
    ├── config.py               # extend: add DISCORD_WEBHOOK_URL, NOTIFICATIONS_ENABLED env vars
    ├── models.py                # extend: NotificationRecord dataclass
    ├── storage.py                 # extend: notification_record table + helpers; get_next_showtime_for_movie
    ├── discord_client.py            # new: send_notification(webhook_url, message) — thin requests.post() wrapper
    ├── notify.py                     # new: orchestrates recommendation-state-transition detection -> message build -> deliver -> record, mirrors recommend.py
    └── scheduler.py                   # extend: periodic job also runs notification evaluation each cycle

main.py                                    # extend: run notification evaluation alongside the existing one-shot ingestion + enrichment + recommendation calls

tests/
├── unit/
│   ├── test_discord_client.py
│   └── test_notify.py
```

**Structure Decision**: This feature extends features 001-003's existing
single-project layout. `discord_client.py` and `notify.py` are new files
mirroring the fetch/orchestrate split already established twice
(`tmdb_client.py`/`enrich.py`, `letterboxd_client.py`/`recommend.py`). No
new Docker image, container, or port is introduced. `scheduler.py` is
extended in the same edit style feature 003 already used to add
enrichment + recommendation evaluation to the periodic job — this
feature's notification check is added to that same job, not a new
schedule (per the spec's Assumptions).

## Complexity Tracking

*No violations — table intentionally omitted.*
