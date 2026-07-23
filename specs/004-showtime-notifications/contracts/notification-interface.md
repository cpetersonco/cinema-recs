# Interface Contract: Discord Notification Delivery

This feature's only external interface is the outbound Discord webhook
call it makes; it exposes no new internal module boundary that another
feature consumes (unlike features 002/003, which hand off `tmdb_id` and
`movie_recommendation` respectively to a downstream feature). There is no
new HTTP-facing API on this project's own Flask app either.

## Outbound: Discord webhook `POST {DISCORD_WEBHOOK_URL}`

**Request**: `POST` with JSON body `{"content": "<message>"}`, where
`<message>` is a plain-text string containing (per spec FR-002):

- The movie title
- The movie's next active showtime's date and start time (research.md:
  "which showtime's date/time")
- The specific matched reason(s) from feature 003's
  `movie_recommendation.reasons` (e.g. `watchlist`, `rating`,
  `best_of:official_top_250`), rendered in a human-readable form
- That same showtime's `ticket_url` (spec FR-002a), when present —
  omitted from the message (not a broken/placeholder link) when that
  showtime's `ticket_url` is `None`

**Contract with feature 003**: This feature reads
`storage.get_movie_recommendation(db_path, movie_title)` (feature 003's
contract, `specs/003-showtime-recommendation-rules/contracts/recommendation-interface.md`)
and treats any row where `is_recommended != True` (including no row at
all) exactly as feature 003's contract specifies for its other
consumers: never a notification trigger.

**Contract with feature 001**: The ticket link comes from
`storage.get_next_showtime_for_movie(...)`'s returned `Showtime.ticket_url`
(feature 001's FR-011) — this feature does not resolve or construct a
ticket URL itself.

**Delivery outcome handling** (spec FR-005):
- HTTP 2xx response → delivery recorded as `"sent"`, `notification_record.active`
  set to `true`.
- Any other outcome (non-2xx response, timeout, connection error) →
  delivery recorded as `"failed"`, logged, `notification_record.active`
  left `false` so the next evaluation cycle retries. Ingestion and
  recommendation evaluation are unaffected either way — this call never
  raises out of the notification cycle.

No response body is required or parsed; Discord's webhook endpoint
returns `204 No Content` on success.
