# Interface Contract: Cancellation/Reschedule Alert Delivery

Like feature 004, this feature's only external interface is the same
outbound Discord webhook call (`discord_client.send_notification`, unchanged);
it exposes no new HTTP-facing API. This contract covers the second class
of message this feature adds to that same webhook, and its contract with
feature 004's existing notification state.

## Outbound: Discord webhook `POST {DISCORD_WEBHOOK_URL}` (reused from feature 004)

**Request**: Same shape as feature 004's contract — `POST` with JSON body
`{"content": "<message>"}` — via the same `discord_client.send_notification`
function, unchanged. This feature adds two new message shapes:

**Cancelled message** (spec FR-002) contains at minimum:
- The movie title
- The original showing's date and start time (from the disappeared
  `Showtime` row referenced by `notification_record.notified_showtime_id`)
- A clear statement that the showing was cancelled/removed by the source

**Rescheduled message** (spec FR-003) contains at minimum:
- The movie title
- The original showing's date and start time
- The new showing's date and start time (from
  `storage.get_next_showtime_for_movie`, feature 004's existing helper)
- A clear statement that the showing was rescheduled, not merely
  recommended again

## Contract with feature 004's notification state

**Input**: This feature reads `notification_record` rows where
`active = true` and `notified_showtime_id IS NOT NULL` — i.e., movies
feature 004 has already sent a recommendation notification for, whose
referenced showtime this feature must now watch. It does not evaluate
movies feature 004 has never notified (spec FR-006) and does not
duplicate feature 004's own recommendation-notification logic.

**Trigger condition**: The `Showtime` row identified by
`notified_showtime_id` has `status = 'stale'` (feature 001's existing
lifecycle transition, made by `storage.mark_stale_showtimes()` during
that cycle's ingestion step, which always runs before notification
evaluation per `scheduler.py`'s job ordering).

**Classification** (data-model.md's State Transitions #2/#3):
- `storage.get_next_showtime_for_movie(db_path, cinema_id, movie_title)`
  returns `None` → cancelled.
- Returns a `Showtime` → rescheduled, using that showtime's date/time as
  the new time.

**Delivery outcome handling** (spec FR-007, mirroring feature 004's
FR-005 exactly):
- HTTP 2xx → `disappearance_alerted` set `true` (cancelled case) or
  `notified_showtime_id` updated + `disappearance_alerted` reset `false`
  (rescheduled case, data-model.md #3); `last_delivery_outcome` →
  `"sent"`.
- Any failure (non-2xx, timeout, connection error) → logged,
  `disappearance_alerted` left `false` (cancelled case) /
  `notified_showtime_id` left pointing at the stale showtime
  (rescheduled case) so the next cycle retries; `last_delivery_outcome`
  → `"failed"`. Ingestion and recommendation evaluation are unaffected
  either way — this call never raises out of the notification cycle,
  same as feature 004's existing behavior.

**Idempotency** (spec FR-004): Once `disappearance_alerted = true` for a
given `notified_showtime_id`, this feature's loop skips that movie until
either `notified_showtime_id` changes (reschedule) or `active` resets to
`false` (movie drops out of recommended entirely — feature 004's
existing path, which also clears `notified_showtime_id` and
`disappearance_alerted` per data-model.md #5).

No response body is required or parsed — same as feature 004's contract.
