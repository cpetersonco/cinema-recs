# Research: Showtime Cancellation & Reschedule Alerts

No open `NEEDS CLARIFICATION` markers came out of Technical Context —
this feature is a narrow extension of feature 004's already-implemented
notification pipeline, so research here is confirming the integration
points in the existing code rather than evaluating new technology
choices.

## Decision: Detect disappearance by re-checking the referenced showtime's status, not by diffing scrape output

**Decision**: On each notification-evaluation cycle, for every
`NotificationRecord` with `active = true` (i.e., a movie currently
carrying an un-superseded recommendation notification) and a stored
`notified_showtime_id`, look up that specific `Showtime` row by id and
check its `status` column.

**Rationale**: Feature 001 already transitions a showtime from `active`
to `stale` in `storage.mark_stale_showtimes()` whenever an ingestion run
no longer finds it published (`src/cinema_recs/storage.py:218`). This
feature needs no new scraping, diffing, or event stream — it only needs
to notice, after that transition has already happened, that a specific
showtime id it previously referenced is no longer `active`. Keying off
the row's own `status` column (rather than comparing scrape output
before/after) reuses existing, already-tested state instead of
duplicating it.

**Alternatives considered**:
- *Diff the scraped set directly in `ingest.py`*: rejected — would
  couple notification logic into the scraper/ingestion module, which
  feature 001 owns and which has no concept of "was this notified."
  Checking status from `notify.py` (which already owns
  notification-record state) keeps the concern in one place, matching
  feature 004's existing module boundary.
- *Poll `list_active_showtimes()` and infer absence by set membership*:
  rejected — more code and an extra full-table scan per cycle for the
  same answer a single indexed lookup by `showtime.id` already gives.

## Decision: Classify cancelled vs. rescheduled via `get_next_showtime_for_movie`, reused as-is

**Decision**: When the referenced showtime is found `stale`, call the
existing `storage.get_next_showtime_for_movie(db_path, cinema_id,
movie_title)` (already used by feature 004 to pick the showtime for the
original recommendation notification, `storage.py:636`). `None` →
cancelled (FR-002). A `Showtime` → rescheduled, with that showtime's
date/time as the "new" time (FR-003).

**Rationale**: This is exactly the "movie's single earliest upcoming
active showtime" rule the spec's Edge Cases section calls for, and it's
already implemented and tested by feature 004 — reusing it means zero
new query logic for the reschedule case.

**Alternatives considered**: Matching the new showtime to the old one by
similarity (nearest date, same format) was considered and rejected in
the spec's own Assumptions — the source exposes no explicit reschedule
event, so any similarity heuristic would be a guess dressed up as
precision. "Any other active showtime, earliest first" is simpler and
matches what the operator would actually check on the listing page
themselves.

## Decision: Extend `notification_record` with additive columns, not a new table

**Decision**: Add `notified_showtime_id` (nullable INTEGER, references
`showtime.id`) and `disappearance_alerted` (INTEGER/boolean, default 0)
to the existing `notification_record` table, following the same
`ALTER TABLE ... ADD COLUMN` migration pattern feature 001 already used
for `showtime.ticket_url` (`storage.py:128-134`,
`_migrate_add_showtime_ticket_url`).

**Rationale**: `notification_record` already tracks "has this movie been
notified, and is that notification still the live one" — this feature
only needs two more facts about that same row (which showtime, and
whether its disappearance was already alerted), not a new entity with
its own lifecycle. A second table would need its own foreign key back to
`notification_record` and duplicate the same `movie_title` keying for no
benefit.

**Alternatives considered**: A separate `showtime_alert` table keyed by
`showtime_id` was considered, since in principle a single movie could in
future have more than one independently-tracked notified showtime.
Rejected as premature for this feature: feature 004's model is
deliberately one active notification per movie at a time (spec 004
FR-003), so `notification_record` already has a 1:1 shape with "the
current notified showtime" and a second table would be an abstraction
with no current second use (Constitution IV).

## Decision: Run disappearance detection inside `notify.py`'s existing `run_notifications()`, as a second pass after the existing recommendation pass

**Decision**: Add a second loop to `run_notifications()` (or a helper it
calls) that runs after the existing per-movie recommendation-notification
loop, iterating movies with `active = true` notification records instead
of `list_matched_movie_titles()`.

**Rationale**: `scheduler.py`'s per-cycle job already calls
`run_notifications(config.db_path, cinema.id, config)` once per cycle
(`scheduler.py:35`) after ingestion, enrichment, and recommendation
evaluation — exactly the ordering this feature needs, since disappearance
can only be detected after that cycle's `mark_stale_showtimes()` call
inside `run_ingestion()` has already run. No scheduler change is needed.

**Alternatives considered**: A new `run_disappearance_alerts()` function
called separately from `scheduler.py` was considered for separation of
concerns, but rejected — it would require the scheduler to know about
and sequence two notification-related calls instead of one, for a split
that doesn't correspond to any real independent deployment or testing
need (both passes share the same webhook config, same enable/disable
switch, same cycle). Kept as one entry point per Constitution IV.
