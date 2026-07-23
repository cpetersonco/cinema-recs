# Feature Specification: Showtime Cancellation & Reschedule Alerts

**Feature Branch**: `005-showtime-cancellation-alerts`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "I want to be notified as soon as a new showtime is detected and recommended. also handle showing getting cancelled or rescheduled from the source."

## User Scenarios & Testing *(mandatory)*

<!--
  Note: "notified as soon as a new showtime is detected and recommended"
  is already delivered by feature 004 (Showtime Notifications), which
  ships a Discord alert the first time one of a movie's showtimes is
  observed as recommended. This feature covers the remaining, unbuilt
  half of the request: what happens after that initial alert, when the
  source cinema cancels or reschedules the specific showing the operator
  was told about.
-->

### User Story 1 - Get notified when an already-alerted showing is cancelled (Priority: P1)

As the operator, after I've been alerted that a showtime is worth
seeing, I want to be told if the cinema pulls that showing before I buy
a ticket, so I don't plan around a screening that no longer exists.

**Why this priority**: A stale "go see this" alert that silently stops
being true is worse than no alert at all — it actively misleads the
operator. This is the core risk this feature exists to close.

**Independent Test**: Can be fully tested by letting a showtime be
recommended and notified (per feature 004), then removing it from a
subsequent ingestion run so it transitions to `stale` with no other
active upcoming showtime for that movie, and confirming a "cancelled"
Discord notification is sent referencing the original showing's date and
time.

**Acceptance Scenarios**:

1. **Given** a movie's showtime was previously the subject of a
   recommendation notification, **When** a later ingestion run no longer
   finds that showtime published and the movie has no other active
   upcoming showtime, **Then** a Discord notification is sent stating
   that showing was cancelled, identifying the movie and the original
   date/time.
2. **Given** a showtime was never recommended or notified, **When** it
   stops being published by the source, **Then** no cancellation
   notification is sent for it.

---

### User Story 2 - Get notified when an already-alerted showing is rescheduled (Priority: P1)

As the operator, I want to be told the new date/time when a showing I
was alerted about disappears from the source but the same movie still
has another upcoming showing, so I can adjust my plans instead of
assuming it was cancelled outright.

**Why this priority**: Distinguishing "moved" from "gone" matters
operationally — treating every disappearance as a flat cancellation
would cause the operator to give up on a movie that's actually still
showing, just at a different time.

**Independent Test**: Can be fully tested by letting a showtime be
recommended and notified, then in a later ingestion run removing that
specific showtime while a different active upcoming showtime for the
same movie remains (or newly appears), and confirming a "rescheduled"
Discord notification is sent with both the original and new date/time.

**Acceptance Scenarios**:

1. **Given** a movie's notified showtime is no longer published,
   **When** that movie still has another active upcoming showtime at
   the time of the check, **Then** a Discord notification is sent
   stating the showing was rescheduled, including the original
   date/time and the new earliest upcoming active date/time.
2. **Given** a rescheduled notification has been sent for a movie,
   **When** that movie's new showtime later also disappears with no
   further active upcoming showtime remaining, **Then** a separate
   cancellation notification is sent (the reschedule notification does
   not suppress a later cancellation).

---

### User Story 3 - Avoid duplicate cancellation/reschedule alerts (Priority: P2)

As the operator, I want at most one cancellation-or-reschedule
notification per disappearance event, not one per ingestion run it
remains gone, so I'm not repeatedly told the same showing vanished.

**Why this priority**: Without this, every ingestion cycle after a
showing disappears would re-fire the same alert, which is noisy but not
misleading — lower stakes than the P1 stories, but still needed for the
feature to be usable day to day.

**Independent Test**: Can be fully tested by letting a notified showtime
go stale, confirming one cancellation/reschedule alert fires, then
running ingestion several more times with the showtime still absent and
confirming no repeat alert is sent.

**Acceptance Scenarios**:

1. **Given** a cancellation or reschedule notification has already been
   sent for a given showtime's disappearance, **When** subsequent
   ingestion runs still don't find that showtime, **Then** no further
   notification is sent for that same disappearance.
2. **Given** the Discord webhook is temporarily unavailable when a
   cancellation/reschedule would be sent, **When** delivery fails,
   **Then** the failure is logged, ingestion is not blocked, and the
   event is not marked as already alerted so a later attempt can still
   succeed.

---

### Edge Cases

- What happens when a notified showtime's movie has *multiple* other
  active upcoming showtimes when the notified one disappears (not just
  one replacement)? The reschedule notification reports the movie's
  single earliest remaining active upcoming showtime, mirroring feature
  004's existing "earliest upcoming showtime" rule for the original
  recommendation notification.
- What happens when a showtime that was reported cancelled or
  rescheduled later reappears in the source (e.g., the cinema restores
  it)? This is treated the same way feature 001 already treats a
  reappearing stale showtime — it becomes `active` again — but no new
  Discord notification is sent for the reappearance itself; only a
  future disappearance would notify again.
- What happens when the Discord webhook is unreachable when a
  cancellation/reschedule alert would fire? Ingestion and recommendation
  evaluation must complete normally regardless; the failure is logged,
  matching feature 004's existing failure-handling pattern.
- What happens when notifications are disabled (per feature 004's
  configuration switch)? No cancellation/reschedule alerts are sent
  either, consistent with the same on/off switch covering all
  notification types from this feature area.
- What happens when a movie was notified as recommended, then the
  *specific* notified showtime is replaced by a new showtime for the
  same movie at the *same* date/time but a different format (e.g.,
  Standard becomes 4DX)? This still counts as a disappearance of the
  original showtime record (per feature 001's uniqueness key, which
  includes format) and is reported as a reschedule, even though the
  date/time may be identical — the notification will show the format
  change via the new showing's details.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST detect, as part of each ingestion/
  recommendation-evaluation cycle, when a showtime that was the subject
  of a prior recommendation notification (per feature 004) is no longer
  found active in the source.
- **FR-002**: When such a showtime disappears and the movie has no other
  active upcoming showtime, the system MUST send a Discord notification
  identifying it as cancelled, including the movie title and the
  original showing's date and time.
- **FR-003**: When such a showtime disappears and the movie still has
  another active upcoming showtime, the system MUST send a Discord
  notification identifying it as rescheduled, including the movie title,
  the original showing's date/time, and the movie's new single earliest
  upcoming active showtime's date/time.
- **FR-004**: The system MUST send at most one cancellation-or-reschedule
  notification per disappearance event; it MUST NOT re-notify on
  subsequent cycles for the same showtime remaining absent.
- **FR-005**: A movie that receives a reschedule notification and is
  later notified again as newly recommended or later has its
  replacement showtime also disappear MUST be eligible for further
  cancellation/reschedule notifications — reschedule notifications do
  not permanently suppress future alerts for that movie.
- **FR-006**: The system MUST NOT send a cancellation or reschedule
  notification for any showtime that was never the subject of a
  recommendation notification.
- **FR-007**: The system MUST NOT block or fail ingestion or
  recommendation evaluation when cancellation/reschedule notification
  delivery fails; the failure MUST be logged, and the event MUST NOT be
  marked as already alerted so a later attempt can still succeed.
- **FR-008**: The system MUST NOT send cancellation or reschedule
  notifications when notifications are disabled via feature 004's
  existing enable/disable configuration; no separate on/off switch is
  introduced for this feature.

### Key Entities

- **Notification Record** (extends feature 004's entity): in addition to
  tracking that a movie was notified as recommended, MUST now also
  record which specific showtime (date, start time, format) was
  referenced in that notification, so a later ingestion cycle can detect
  when that specific showing disappears and distinguish "still exists
  elsewhere" (reschedule) from "gone entirely" (cancelled). MUST also
  track whether a cancellation/reschedule alert has already been sent
  for that showing's disappearance, to satisfy FR-004.

### Dependencies

- **Hard dependency on feature 004** (Showtime Notifications): this
  feature only evaluates showtimes that feature 004 already sent a
  recommendation notification for; it has no independent trigger and
  cannot function if feature 004 is disabled or has never fired.
- **Hard dependency on feature 001**'s existing active/stale showtime
  lifecycle: cancellation detection relies on feature 001's existing
  transition of a showtime from `active` to `stale` when it's no longer
  found in a scrape; this feature adds no new scraping logic of its own.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When a showing the operator was alerted about is pulled by
  the cinema with no replacement showing for that movie, the operator is
  notified it's cancelled without needing to re-check the listing view.
- **SC-002**: When a showing the operator was alerted about is pulled
  but the same movie still has another upcoming showing, the operator is
  notified of the new date/time rather than being left to assume the
  movie is no longer playing.
- **SC-003**: A given showing's disappearance generates exactly one
  cancellation-or-reschedule notification, not one per ingestion cycle
  it remains absent.
- **SC-004**: Ingestion and recommendation evaluation complete normally
  even when cancellation/reschedule notification delivery fails
  entirely.
- **SC-005**: No cancellation or reschedule notification is ever sent
  for a showtime that was never part of a recommendation notification,
  or while notifications are disabled.

## Assumptions

- Only showtimes that already triggered a feature-004 recommendation
  notification are eligible for cancellation/reschedule alerts. Alerting
  on every disappearance of every showtime at the cinema (recommended or
  not) would reproduce the exact noise problem feature 004's P2 story
  was designed to avoid, and would alert the operator about movies they
  were never told to care about in the first place.
- "Rescheduled" vs. "cancelled" is determined solely by whether the
  movie still has *any* other active upcoming showtime at the moment the
  originally-notified showtime disappears — not by matching the new
  showtime to the old one by similarity of date/time. The source
  (feature 001's scraper) does not expose an explicit reschedule event;
  this is an inference from the existing active/stale lifecycle.
- Cancellation/reschedule notifications are sent as new, separate
  Discord messages, not edits to the original recommendation message —
  consistent with this project's webhook-based (fire-and-forget)
  delivery, which does not track message IDs for later editing.
- This feature reuses feature 004's single global enable/disable
  configuration and Discord webhook destination; it does not introduce
  a separate configuration surface.
- Evaluation runs as part of the same ingestion/recommendation-
  evaluation cycle as feature 004, not on a separate schedule.
