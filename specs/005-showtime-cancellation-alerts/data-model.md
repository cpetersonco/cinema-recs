# Data Model: Showtime Cancellation & Reschedule Alerts

This feature extends one existing entity from feature 004
(`specs/004-showtime-notifications/data-model.md`); it introduces no new
tables.

## NotificationRecord (extended)

Tracks, per movie, whether its current "recommended" status has already
triggered a notification (feature 004) — now also tracking which
specific showtime that notification referenced, and whether that
showtime's later disappearance has already triggered a
cancelled/rescheduled alert (this feature).

| Field | Type | Notes |
|---|---|---|
| `id` | integer, primary key | unchanged |
| `movie_title` | text, not null, unique | unchanged |
| `active` | boolean, not null | unchanged — whether the movie is currently within a continuous notified-recommended span (feature 004 FR-003) |
| `notified_at` | timestamp, nullable | unchanged |
| `last_delivery_outcome` | text, nullable | unchanged — `sent` or `failed`, for the most recent notification of any kind (recommendation or cancellation/reschedule) sent for this movie |
| `notified_showtime_id` | integer, nullable, references `showtime.id` | **new** — the specific showtime referenced in the movie's current active recommendation notification (from feature 004's `get_next_showtime_for_movie` at the time it was sent). Cleared (`NULL`) whenever `active` is reset to `false`, since there is no longer a "current" showtime to track disappearance for. |
| `disappearance_alerted` | boolean, not null, default `false` | **new** — whether a cancelled/rescheduled alert has already been sent for `notified_showtime_id`'s disappearance (spec FR-004). Reset to `false` whenever `notified_showtime_id` changes (a new recommendation notification, or a rescheduled alert that updates the tracked showtime — see State Transitions). |

**Migration**: Both new columns are added via
`ALTER TABLE notification_record ADD COLUMN ...` inside
`storage.init_schema()`, following the existing
`_migrate_add_showtime_ticket_url` pattern — additive, no-op on a fresh
database (already present in `CREATE TABLE IF NOT EXISTS`), safe against
existing rows on an upgraded database (`notified_showtime_id` defaults
`NULL`, `disappearance_alerted` defaults `false`, so pre-existing
records are simply not eligible for a disappearance alert until their
next recommendation notification populates `notified_showtime_id`).

### State Transitions (this feature's additions to feature 004's existing lifecycle)

1. **A recommendation notification is sent** (feature 004's existing
   path): `active` → `true`, `notified_showtime_id` → the showtime just
   referenced, `disappearance_alerted` → `false`.
2. **The referenced showtime (`notified_showtime_id`) transitions to
   `stale`, and the movie has no other active upcoming showtime**:
   `disappearance_alerted` → `true` after a successful "cancelled"
   delivery. `active` and `notified_showtime_id` are left as-is (still
   pointing at the now-stale showtime) — there's nothing left to
   supersede it with, and leaving them intact keeps `disappearance_alerted`
   meaningful as "already told the operator about this specific
   showtime's disappearance."
3. **The referenced showtime transitions to `stale`, and the movie has
   another active upcoming showtime**: after a successful "rescheduled"
   delivery, `notified_showtime_id` → the new showtime's id,
   `disappearance_alerted` → `false` (so if *that* showtime later also
   disappears, a further alert can fire — spec User Story 2, Acceptance
   Scenario 2).
4. **Delivery of a cancelled/rescheduled alert fails**: no fields change
   (`disappearance_alerted` stays `false`), so the next cycle retries —
   mirrors feature 004's existing FR-005 pattern for recommendation
   notifications (spec FR-007).
5. **The movie drops out of "recommended" entirely** (feature 004's
   existing path, unchanged): `active` → `false`. `notified_showtime_id`
   is cleared to `NULL` and `disappearance_alerted` reset to `false`,
   since there's no longer a "current" notified showtime to track.

## Relationships

```
Showtime (1) ──< (0..1) NotificationRecord.notified_showtime_id
```

`notified_showtime_id` is a soft reference (nullable, no `ON DELETE`
behavior needed since `Showtime` rows are never deleted — only
transitioned between `active`/`stale` per feature 001's data model).
