# Feature Specification: Showtime Notifications

**Feature Branch**: `004-showtime-notifications`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "3. Notifications — alert when a movie/format you care about gets a showtime (e.g., Discord via your existing Tower alerting setup)."

## Clarifications

### Session 2026-07-22

- Q: Should this feature use its own dedicated watchlist of specific movie titles, or should it instead notify whenever a showtime becomes "recommended" per feature 003's genre/rating/new-release criteria (no separate watchlist)? → A: Trigger off feature 003's recommendation criteria — no separate watchlist. This makes feature 003 a hard prerequisite for this feature, and means "format you care about" (from the original request) is **not** covered, since feature 003 has no format criterion — see Assumptions.
- Q (via feature 003's clarification session, propagated here): feature 003's criteria changed from genre/rating(TMDB)/new-release to Letterboxd-based watchlist/rating/best-of-list, and each recommendation now records which specific criterion (or criteria) matched. → A: This feature's notifications MUST surface that matched reason (e.g., "on your watchlist," "rated 4.9 on Letterboxd," "on Letterboxd's Top 250") rather than just announcing "recommended" with no explanation.
- Q: A recommended movie can have many active showtimes — which one's date/start time appears in the notification? → A: The movie's single earliest upcoming active showtime (the one the operator would act on first to get tickets), not every showing and not specifically the showing that triggered the recommendation.
- Q: When a Discord webhook URL is configured but the enable/disable switch is left unset, should notifications be on or off by default? → A: On by default — configuring a webhook URL is itself the opt-in signal; the switch exists to pause delivery without discarding the URL, not to require a second explicit opt-in.
- Q: Should the notification also include a direct ticket-purchase link for the specified showtime? → A: Yes. This requires feature 001 to capture a per-showing ticket URL, which it does not do today — feature 001's spec has been amended (FR-011) to add this as a new, best-effort requirement (absent when the source doesn't expose one, never fabricated). This feature's notification MUST include that URL when feature 001 has captured one for the referenced showtime, and MUST render normally without a link when it hasn't (mirroring the existing "no broken section" pattern used for missing metadata elsewhere in this project).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get notified when a showtime becomes recommended (Priority: P1)

As the operator, I want to be notified via Discord when a showtime
becomes recommended (per feature 003's watchlist/rating/best-of-list
criteria) and to see *why* it was recommended, so I find out without
having to check the listing view myself, and understand at a glance
whether it's worth pursuing tickets.

**Why this priority**: This is the core value of the feature — being
told, rather than having to look. Without it, the feature delivers
nothing beyond what the listing view (features 001-003) already
provides.

**Independent Test**: Can be fully tested by configuring a feature-003
preference that matches a specific ingested movie, letting recommendation
evaluation mark its showtime recommended, and confirming a Discord
notification is sent containing the movie title, date, and start time.

**Acceptance Scenarios**:

1. **Given** a showtime is newly marked recommended by feature 003,
   **When** the next notification check runs, **Then** a Discord
   notification is sent identifying the movie, date, start time, and the
   specific matched reason(s) (e.g., "on your Letterboxd watchlist").
2. **Given** a showtime is not marked recommended, **When** the
   notification check runs, **Then** no notification is sent for it.
3. **Given** a showtime matches more than one criterion (e.g., it's both
   on the watchlist and above the rating threshold), **When** the
   notification is sent, **Then** it lists all matched reasons, not just
   one.

---

### User Story 2 - Avoid duplicate or noisy notifications (Priority: P2)

As the operator, I want to be notified once when a movie's showtime
first becomes recommended, not once per individual session/showtime or
per re-evaluation, so I'm not spammed with a message for every showing of
the same recommended movie across multiple days.

**Why this priority**: Without this, a recommended movie playing daily
for a month, or recommendation logic simply re-running, would generate a
notification every single cycle, making the feature actively annoying
rather than useful.

**Independent Test**: Can be fully tested by having a movie's showtimes
remain recommended across several ingestion/re-evaluation cycles and
confirming only one notification is ever sent for that movie, not one per
showtime or per evaluation run.

**Acceptance Scenarios**:

1. **Given** a movie already triggered a notification for one of its
   recommended showtimes, **When** more of its showtimes are ingested or
   recommendations are re-evaluated later, **Then** no further
   notification is sent for that movie unless it had stopped being
   recommended and newly becomes recommended again.
2. **Given** the Discord webhook is temporarily unavailable, **When** a
   newly recommended movie's showtime would trigger a notification,
   **Then** the failure is logged and does not block ingestion, and does
   not silently mark the movie as already notified.

---

### User Story 3 - Configure notification delivery (Priority: P3)

As the operator, I want to configure where notifications are sent (a
Discord webhook URL) and be able to turn notifications off entirely,
without a code change or redeploy.

**Why this priority**: Delivery configuration is necessary for the
feature to be usable at all in a given deployment, but it's a smaller
concern than the notification logic itself (P1/P2), and turning
notifications off entirely is a reasonable but secondary need.

**Independent Test**: Can be fully tested by configuring a webhook URL,
confirming notifications are delivered there, then disabling
notifications and confirming no further notifications are sent even
when new recommended showtimes appear.

**Acceptance Scenarios**:

1. **Given** a Discord webhook URL is configured, **When** a showtime
   becomes recommended, **Then** the notification is delivered to that
   webhook.
2. **Given** notifications are disabled in configuration, **When** a
   showtime becomes recommended, **Then** no notification is sent.

---

### Edge Cases

- What happens when Discord's webhook is unreachable or misconfigured?
  Ingestion and recommendation evaluation must still complete normally;
  the notification failure should be logged and visible the same way
  ingestion/enrichment failures are (per features 001/002's
  observability pattern).
- What happens when a movie's showtime becomes recommended, then stops
  being recommended (e.g., a preference changes), then becomes
  recommended again later? This should be treated as a new
  notification-worthy event, not suppressed as a duplicate.
- What happens when no preferences are configured in feature 003 (so
  nothing is ever recommended)? No notifications should ever be sent,
  and this should not be treated as an error.
- **"Format you care about" is not covered by this feature.** The
  original request mentioned being notified about a format (e.g., 4DX)
  you care about, but feature 003's recommendation criteria (watchlist,
  Letterboxd rating, best-of list membership) have no format dimension,
  and feature 001's `format` field is presently always empty regardless.
  Format-based notification would need its own criterion added to
  feature 003 (or a separate mechanism) as future work.
- What happens when a matched showtime's recommendation reason data is
  missing or malformed (e.g., feature 003 marked it recommended but the
  matched-reason record is empty)? The notification should still send
  with whatever reason information is available rather than failing to
  notify at all, since a notification with an incomplete reason is still
  more useful than no notification.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST send a Discord notification when a
  showtime is newly marked recommended by feature 003's recommendation
  logic.
- **FR-002**: Each notification MUST contain at minimum the movie title,
  the date and start time of that movie's single earliest upcoming
  active showtime (not every active showtime, and not necessarily the
  specific showtime whose ingestion triggered the recommendation), and
  the specific matched reason(s) recorded by feature 003 (on watchlist /
  rating above threshold / on a best-of list) — not just the fact that
  it was recommended.
- **FR-002a**: The notification MUST include a direct ticket-purchase
  link for that same showtime when feature 001 has captured one (per
  feature 001's FR-011), and MUST render normally without a link — not
  with a broken or placeholder link — when feature 001 has not captured
  one for that showtime.
- **FR-003**: The system MUST send at most one notification per movie —
  the first time one of its showtimes is newly observed as
  recommended — and MUST NOT re-notify for additional recommended
  showtimes of a movie already notified, unless that movie had
  previously stopped being recommended and has newly become recommended
  again.
- **FR-004**: The system MUST NOT send any notification for a showtime
  that is not marked recommended.
- **FR-005**: The system MUST NOT block or fail showtime ingestion or
  recommendation evaluation when Discord notification delivery fails
  (e.g., webhook unreachable); the failure MUST be logged, and the movie
  MUST NOT be marked as already notified so a later attempt can still
  succeed.
- **FR-006**: The system MUST allow the operator to configure the
  Discord webhook destination, and to disable notifications entirely,
  without requiring an application rebuild or redeploy. Notifications
  MUST be considered enabled by default once a webhook destination is
  configured; the disable switch is for pausing delivery without
  discarding the configured destination, not a second required opt-in.
- **FR-007**: The system MUST NOT send any notification when
  notifications are disabled, or when feature 003 has no configured
  preferences (so nothing is ever recommended).

### Key Entities

- **Notification Record**: Tracks whether a given movie's current
  "recommended" status has already triggered a notification, so
  re-evaluation or additional showtimes for the same movie don't
  re-notify while it remains continuously recommended. Attributes: movie
  title, notified-at timestamp, delivery outcome (sent/failed), and the
  recommended-state transition it corresponds to (so a
  recommended→not-recommended→recommended cycle can notify again).

### Dependencies

- **Hard dependency on feature 003** (Showtime Recommendation Rules):
  this feature has no independent trigger of its own — it only reacts to
  feature 003's "recommended" status and matched-reason data. Feature
  003 must exist and be configured (a Letterboxd username and/or rating
  threshold) for any notification to ever be sent. Feature 003 depends
  on feature 002 (TMDB enrichment) — not for genre/rating data, but
  because feature 002's TMDB match is how feature 003 locates a movie's
  Letterboxd entry — so **feature 002 is a transitive dependency of this
  feature too**, via feature 003.
- **Soft dependency on feature 001's FR-011** (per-showing ticket URL):
  the ticket-link portion of a notification (FR-002a) depends on feature
  001 having captured a `ticket_url` for the relevant showtime. Unlike
  the feature 003 dependency, this is not a hard blocker for the feature
  overall — per FR-002a, a notification still sends normally (title,
  date/time, reasons) without a link when feature 001 hasn't captured
  one for that showing. Feature 001's spec has been amended for this
  (see its Clarifications session); feature 001's plan/tasks/research
  still need their own follow-up amendment to actually implement FR-011
  before any notification can include a real link — this is separate,
  prerequisite work not covered by this feature's own tasks.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When a showtime becomes recommended, the operator receives
  a Discord notification — including why it was recommended — without
  needing to check the listing view themselves.
- **SC-002**: A movie remaining recommended across many showtimes,
  ingestion runs, or re-evaluations generates exactly one notification,
  not one per showtime or per evaluation.
- **SC-003**: Ingestion and recommendation evaluation complete normally
  even when Discord notification delivery fails entirely.
- **SC-004**: Disabling notifications or changing the webhook
  destination takes effect within one cycle, without any code or
  deployment change.
- **SC-005**: No notification is ever sent for a non-recommended
  showtime, and none are sent when notifications are disabled or no
  feature-003 preferences are configured.

## Assumptions

- A notification fires at most once per movie for each continuous
  span of being recommended — not once per individual showtime/session
  and not once per re-evaluation cycle — to avoid repeated notifications
  for a movie playing (and remaining recommended) across many days. If a
  movie stops being recommended and later becomes recommended again,
  that counts as a new notification-worthy event.
- Notifications are delivered via a Discord webhook URL supplied through
  configuration (consistent with this project's env-var-driven config
  pattern) — this may point at the same Discord server/channel used by
  the operator's existing Tower infrastructure alerting, but this
  feature does not integrate with Grafana/Tower's alerting pipeline
  directly; it sends its own webhook calls.
- This is a single-operator personal project; notification configuration
  (webhook URL, enabled/disabled) is one global configuration, not
  per-user.
- Notification evaluation runs as part of the existing
  ingestion/recommendation-evaluation cycle, not on a separate schedule.
- **Format-based notification is out of scope** for this feature (see
  Edge Cases) since feature 003 does not evaluate format, and feature
  001 does not yet populate format data. This is a known gap relative to
  the original feature request, not an oversight.
- This feature depends on feature 003 (recommendation rules), which in
  turn depends on feature 001 (showtime ingestion) for movie titles, and
  on feature 002 (TMDB enrichment) as the mechanism for locating each
  movie's Letterboxd entry. So all three prior features (001, 002, 003)
  are transitive prerequisites of this feature.
- Notification reason text is derived directly from feature 003's
  Showtime Recommendation Status matched-reason data (see feature 003's
  spec) rather than being recomputed independently here.
