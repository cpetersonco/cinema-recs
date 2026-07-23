# Data Model: Showtime Notifications

This table extends the existing SQLite schema (same `cinema_recs.db`
file used by features 001-003). Like feature 003's tables, identity here
is the `movie_title` string (the join key back to `showtime.movie_title`,
`movie_metadata.movie_title`, and `movie_recommendation.movie_title`).

## Notification Record

Tracks whether a movie's *current, continuous* span of being recommended
has already triggered a notification (spec FR-003, Key Entities).

| Field | Type | Notes |
|---|---|---|
| `id` | integer, primary key | |
| `movie_title` | text, not null, unique | Join key, same convention as `movie_recommendation.movie_title` |
| `active` | integer (0/1), not null | `true` once a notification has been sent for the *current* recommended span; reset to `false` the moment the movie is observed no-longer-recommended (research.md) |
| `notified_at` | timestamp, nullable | Set on a successful send; not updated on failed attempts |
| `last_delivery_outcome` | text, nullable | `"sent"` or `"failed"` — the most recent delivery attempt's outcome, for observability (mirrors feature 001/002's attempt-outcome logging pattern) |

**Uniqueness rule**: `movie_title` is unique — one current notification
state per movie.

**State transition rule** (spec FR-003, Edge Cases):

```
not recommended --(becomes recommended)--> notify, active=true
active=true, still recommended --(re-evaluated)--> no-op (already active)
active=true --(becomes not recommended)--> active=false (reset, no notification)
active=false, becomes recommended again --(becomes recommended)--> notify again, active=true
```

A failed delivery attempt (`last_delivery_outcome = "failed"`) leaves
`active = false`, so the very next evaluation cycle naturally retries the
send — no separate retry/backoff mechanism is needed (research.md).

## Relationships

```
Movie Recommendation.movie_title (feature 003, is_recommended=True)
  ──> (drives) Notification Record.movie_title
Showtime.movie_title (feature 001, status="active")
  ──> (supplies date/time AND ticket_url for) the notification body — the
      movie's single earliest active showtime, not stored on
      Notification Record itself (research.md: "which showtime's
      date/time"; FR-002a's ticket link is the same Showtime row's
      existing `ticket_url` field, per feature 001's FR-011 — no new
      field here)
```

No foreign key constraints are added, consistent with features 002/003's
title-string-keyed join pattern.

## Notification Configuration

Not a database table — process configuration, following the established
env-var pattern (features 001-003):

| Env var | Purpose | Required |
|---|---|---|
| `DISCORD_WEBHOOK_URL` | Destination for notification delivery (FR-006) | No — no URL means notifications never fire (FR-007) |
| `NOTIFICATIONS_ENABLED` | Explicit on/off switch, independent of URL presence (FR-006, research.md) | No — defaults to `true` |
