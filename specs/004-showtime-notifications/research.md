# Phase 0 Research: Showtime Notifications

## Decision: Plain `requests.post()` against Discord's webhook URL (no Discord SDK)

**Rationale**: A Discord webhook is a single `POST` of a small JSON body
(`{"content": "..."}`) to a URL the operator supplies — no bot token, no
gateway connection, no slash-command registration is needed for this
one-directional "send a message" use case. `requests` is already a
project dependency (features 002/003). Adding a Discord SDK (e.g.
`discord.py`) would pull in a full gateway/bot client for a single POST
call, directly against the Simplicity principle — the same reasoning
that kept feature 002 off a TMDB SDK and feature 003 off an HTML-parsing
library.

**Alternatives considered**:
- `discord.py` / `discord-webhook` package: rejected — both are built
  around persistent bot connections or add a dependency for
  functionality `requests.post()` already covers in ~5 lines.
- Routing through the operator's existing Tower/Grafana alerting
  pipeline (mentioned in the original feature request): rejected per the
  spec's Assumptions — this feature sends its own webhook calls; it does
  not integrate with Grafana's alerting API. That pipeline is a
  separate, already-configured system for infrastructure alerts, not
  movie recommendations.

## Decision: Notification identity and dedup is per-movie, not per-showtime

**Rationale**: FR-003/SC-002 require exactly one notification per
*continuous span* of a movie being recommended, regardless of how many
showtimes it has. Since feature 003's `movie_recommendation` is already
computed per `movie_title` (not per showtime), the natural dedup key is
the same `movie_title`. A `notification_record` table tracks, per movie,
whether the *current* recommended span has already been notified
(`active = true`) — set on a successful send, and reset to `false` the
moment the movie is observed no-longer-recommended, so a later
re-entry into "recommended" is treated as a new event (per the spec's
recommended→not-recommended→recommended edge case).

**Alternatives considered**:
- Tracking notification state per-showtime: rejected — directly
  contradicts FR-003/SC-002 ("one per movie", not one per showing).
- A notification log with no "already notified" flag, deduped by
  querying "was there a sent notification for this movie in this
  recommended span": rejected as more complex than a single boolean
  toggled on enter/exit — the state machine here is small enough that a
  flag plus a reset-on-exit is sufficient and simpler to reason about.

## Decision: Which showtime's date/time appears in the notification

**The gap**: FR-002 requires the notification to include "showing date,
start time," but feature 003's recommendation is a per-*movie* fact, not
tied to one specific showtime — a recommended movie can have many active
showtimes.

**Resolution**: The notification includes the movie's single earliest
upcoming active showtime (soonest `show_date`/`start_time` among its
currently-active showtimes) — the one the operator would actually want
to act on first to get tickets. This requires one new storage query
(`get_next_showtime_for_movie`), not a new concept — it reuses the
existing `showtime` table feature 001 already populates.

**Alternatives considered**:
- Listing every active showtime for the movie in one notification:
  rejected as unnecessary noise for the common case (most re-releases
  run a handful of showings) and not required by any FR/acceptance
  scenario, which only ever mention "date, start time" in the singular.
- Notifying once per showtime instead: rejected — this is exactly what
  FR-003/SC-002 forbid.

## Decision: Two independent config knobs — webhook URL and an enabled flag

**Rationale**: FR-006 asks for both "configure the destination" and
"disable notifications entirely." A single "presence of the URL" toggle
would conflate "not yet configured" with "temporarily disabled" — an
operator wanting to pause notifications without discarding their webhook
URL would otherwise have to delete and re-enter it. `NOTIFICATIONS_ENABLED`
(optional, default `true`) is added alongside `DISCORD_WEBHOOK_URL`
(optional); notifications only ever fire when both a URL is configured
*and* the flag isn't explicitly disabled — consistent with FR-007's
"disabled OR no feature-003 preferences configured → never notify."

**Alternatives considered**:
- Webhook URL presence as the sole on/off switch: rejected as covered
  above — doesn't cleanly support "pause without losing config."

## Decision: No retry-with-backoff on webhook delivery failure

**Rationale**: Per FR-005, a failed delivery is logged and the movie is
*not* marked as notified — the next scheduled cycle (same interval as
ingestion/enrichment/recommendation, per the spec's Assumptions) naturally
retries it. Adding immediate in-process retry logic would duplicate that
mechanism for a low-volume, non-latency-sensitive notification (at most a
handful of movies per cycle) — over-engineering relative to Simplicity,
the same reasoning against a token-bucket rate limiter in feature 002.

**Alternatives considered**:
- Immediate retry-with-backoff on failure (mirroring feature 002/003's
  HTTP client retry logic): rejected — those retries exist for
  *transient* single-request flakiness within one lookup; here, "try
  again next cycle" is already the correct behavior per FR-005, and is
  simpler than adding a second retry mechanism for the same effective
  outcome.

## Decision: Notification content format

**Rationale**: A single Discord webhook `content` string (plain text,
not a rich embed) containing movie title, date, start time, and matched
reason(s) satisfies FR-002 with the least code. Discord renders plain
webhook messages perfectly readably in a channel; a rich embed is a
cosmetic upgrade with no functional requirement behind it.

**Alternatives considered**:
- Discord embeds (structured fields, colors, thumbnails): rejected for
  this pass — no FR/SC asks for it, and it adds payload-construction
  complexity for a personal-project notification channel. A follow-up if
  the operator wants richer formatting later.

## Decision: Ticket link (FR-002a) requires no new data source

**Rationale**: By the time this feature was planned in detail, feature 001
had already been amended (its own FR-011) to capture a `ticket_url` on
every `Showtime` row when the source provides one
(`.../checkout/seats/{id}`, live-verified). `get_next_showtime_for_movie`
(Phase 2's foundational storage helper) already returns that full
`Showtime` row to build the message's date/time from — its `ticket_url`
field is simply read alongside `show_date`/`start_time`, with no new
query, table, or field required. When that showtime's `ticket_url` is
`None` (feature 001 couldn't determine one), the notification is built
without a link — the same "render normally, don't fabricate" pattern
used everywhere else in this project for optional source-provided data.

**Alternatives considered**:
- Resolving a ticket link independently in this feature (e.g. re-deriving
  it from the movie/showtime some other way): rejected — feature 001 is
  the sole source of showtime data end-to-end; duplicating that lookup
  here would violate the single-source-of-truth pattern already
  established for `movie_metadata`/`movie_recommendation`.
