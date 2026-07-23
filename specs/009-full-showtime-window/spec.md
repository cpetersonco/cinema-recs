# Feature Specification: Full Showtime Window Ingestion

**Feature Branch**: `009-full-showtime-window`

**Created**: 2026-07-23

**Status**: Draft

**Input**: User description: "I'd like to fetch all showtimes available at each of the sources, not just the next day or month. This will affect the cancellation/reschedule logic."

## User Scenarios & Testing *(mandatory)*

<!--
  Today, each source is only ever asked for a narrow slice of its
  published calendar: the Cinepolis scraper defaults to "today" only,
  the Texas Theatre scraper reads whatever calendar page/month it is
  pointed at, and Angelika Dallas returns whatever window its API call
  covers. Because the per-cinema "mark stale" step (feature 005)
  compares every previously-active showtime against what the *current*
  run touched, any showtime scheduled beyond that narrow window gets
  wrongly marked stale — and, per feature 005, can trigger a false
  "cancelled" or "rescheduled" Discord alert — even though the source
  never stopped publishing it. This feature closes that gap by
  fetching each source's complete published showtime calendar on every
  run.
-->

### User Story 1 - See every showtime a source has published, not just the next day or month (Priority: P1)

As the operator, I want each ingestion run to capture every showtime a
source currently has published — today, next week, and next month
alike — so that recommendations and alerts are based on the source's
full calendar instead of an arbitrary near-term slice.

**Why this priority**: This is the entire point of the feature. Without
it, showings further out than the current fetch window are invisible to
the recommendation engine even though the cinema is actively selling
tickets for them.

**Independent Test**: Can be fully tested by running ingestion for a
cinema whose source currently publishes showtimes across multiple
future dates (including dates beyond "tomorrow" or "this calendar
month") and confirming showtimes for all of those dates are captured in
a single run, without needing to re-run ingestion once per day or once
per month.

**Acceptance Scenarios**:

1. **Given** a source has showtimes published for today, next week, and
   next month, **When** an ingestion run executes for that cinema,
   **Then** showtimes from all three time periods are captured in that
   one run.
2. **Given** a source publishes showtimes only through a certain future
   date (its own on-sale horizon), **When** ingestion runs, **Then** no
   error occurs solely because the source's calendar reaches its end —
   ingestion completes normally with everything the source currently
   offers.

---

### User Story 2 - Stop false cancellation/reschedule alerts caused by a narrow fetch window (Priority: P1)

As the operator, I don't want to be told a showing was "cancelled" or
"rescheduled" just because a prior ingestion run only looked at a
narrow window and didn't happen to re-fetch a showing that is still on
sale further out.

**Why this priority**: Feature 005's cancellation/reschedule alerts are
only trustworthy if "not seen in this run" reliably means "the source
stopped publishing it." A narrow fetch window makes that assumption
false and produces misleading alerts — the exact failure mode feature
005 exists to prevent for real cancellations. Tied for top priority with
Story 1 because fetching the full window has no value if the stale-
marking logic still can't trust it.

**Independent Test**: Can be fully tested by seeding a showtime dated
several weeks out that a prior narrow-window run had not re-touched,
running ingestion with the full-window fetch, and confirming that
showtime is re-captured (not marked stale) as long as the source still
publishes it — with no cancellation/reschedule notification sent for
it.

**Acceptance Scenarios**:

1. **Given** a showtime dated 3 weeks from now is still published by
   the source, **When** a full-window ingestion run executes, **Then**
   that showtime remains `active` and no cancellation or reschedule
   notification is sent for it.
2. **Given** a showtime that was previously captured is no longer
   present anywhere in the source's full published calendar, **When**
   ingestion runs, **Then** it is marked stale and the existing
   cancellation/reschedule notification logic from feature 005 applies
   exactly as before.

---

### User Story 3 - Ingestion stays reliable when a source's full calendar is large or slow to fetch (Priority: P2)

As the operator, I want fetching a source's entire published calendar to
fail safely (without corrupting existing data) if the source is slow,
paginated, or temporarily unavailable partway through, so one bad
ingestion run doesn't wipe out showtimes that were successfully
captured before.

**Why this priority**: Fetching more data across more pages/requests
than before increases the odds of a partial failure mid-run. This
guards operational reliability once the wider fetch is in place, but
the feature is still useful without it as long as failures are visible
rather than silently corrupting data.

**Independent Test**: Can be fully tested by simulating a source
becoming unavailable after returning some, but not all, of its
published showtime pages/dates, and confirming the ingestion run is
recorded as a failure or partial outcome (per the existing outcome
model) without marking any previously-active showtime stale for that
run.

**Acceptance Scenarios**:

1. **Given** a source stops responding partway through fetching its
   full calendar, **When** the ingestion run ends, **Then** the run is
   recorded as `failure` (or `partial`, consistent with existing
   outcome semantics) and no previously-active showtime for that cinema
   is marked stale as a result of that incomplete run.
2. **Given** a source's full calendar spans many requests or pages,
   **When** ingestion runs successfully, **Then** all pages/dates are
   combined into one logical run before stale-marking is evaluated, not
   evaluated page-by-page.

---

### Edge Cases

- What happens when a source's calendar has no defined end date (rolling
  window that regenerates daily) versus one with a hard on-sale horizon
  (e.g., tickets only released a fixed number of weeks out)? Both must
  be treated as "fetch everything currently available," not a fixed
  number of days.
- How does the system handle a source that publishes so few showtimes
  further out that today's narrow-window behavior and the new
  full-window behavior would look identical? No special handling needed
  — the full fetch should simply return what's there.
- What happens if a source's full calendar is temporarily empty (e.g.,
  between scheduling cycles) even though it was non-empty in the
  previous run? Existing zero-showtimes-captured handling applies
  unchanged; this is not treated as a fetch failure.
- What happens when a full-window fetch takes long enough to risk
  overlapping with the next scheduled ingestion run? Out of scope for
  this feature; scheduling cadence is not being changed here.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: For each configured source (Cinepolis, Texas Theatre,
  Angelika Dallas), ingestion MUST fetch every showtime currently
  published by that source, not limited to the next single day or the
  current calendar month.
- **FR-002**: When a source paginates or segments its published
  calendar (e.g., by day or by month), ingestion MUST continue fetching
  additional pages/segments until the source has no further showtimes
  to return, then treat the combined result as one ingestion run.
- **FR-003**: The stale-marking step that flags previously-active
  showtimes as no longer published MUST only run after a full-window
  fetch has completed successfully for that cinema; a showtime must
  never be marked stale because it fell outside a narrower slice that
  was fetched instead of the full calendar.
- **FR-004**: If a full-window fetch fails or is incomplete for a
  cinema, ingestion MUST record that run as a failure or partial
  outcome (consistent with existing outcome recording) and MUST NOT
  mark any previously-active showtime for that cinema stale as a result
  of that incomplete run.
- **FR-005**: The cancellation/reschedule notification logic introduced
  in feature 005 MUST continue to apply unchanged, now operating on the
  full-window stale-marking results rather than narrow-window results.
- **FR-006**: Ingestion MUST NOT impose an artificial cutoff (e.g., "30
  days out") on how far into the future captured showtimes may be —
  the only bound is whatever the source itself currently publishes.

### Key Entities

- **Showtime**: Existing entity (cinema, movie title, date, time,
  format, status) from prior features. This feature changes how far
  into the future showtimes are discovered, not the entity's shape.
- **Ingestion Run**: Existing entity recording per-cinema outcome
  (success/partial/failure) and showtimes captured. This feature
  changes what counts as "complete" for a run — the full published
  calendar rather than a single day/month — but not the entity's shape.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every source, 100% of showtimes currently published
  on that source's site/calendar (at every future date it offers, not
  just the nearest one) are captured within a single ingestion run.
- **SC-002**: The rate of cancellation/reschedule notifications caused
  by a showtime simply falling outside a fetch window (rather than
  genuinely disappearing from the source) drops to zero.
- **SC-003**: An ingestion run that fails partway through fetching a
  source's full calendar never results in a previously-captured,
  still-published showtime being incorrectly marked stale.
- **SC-004**: The operator can see showtimes for a movie at least as far
  out as the source itself publishes them (e.g., a month-ahead
  screening the source has announced is visible immediately after the
  next ingestion run, not only once that date becomes "the next day or
  month").

## Assumptions

- Each source's own on-sale horizon is a source-side business decision
  (theaters generally do not publish showtimes indefinitely into the
  future) — "full window" means everything the source currently
  exposes, not an unbounded/infinite fetch.
- The three existing sources (Cinepolis, Texas Theatre, Angelika
  Dallas) each expose some mechanism (date parameter, calendar page
  navigation, or API pagination) for retrieving showtimes beyond the
  single day/month currently fetched; this feature assumes that
  mechanism exists for each and does not require onboarding a source
  that has no way to enumerate its future showtimes.
- Ingestion cadence (how often the scheduled job runs) is unchanged by
  this feature; only the amount of calendar depth fetched per run
  changes.
- "Complete" for a given run means the full-window fetch for that
  cinema finished successfully; partial fetches are treated as run
  failures per FR-004, not partial successes that still trigger stale-
  marking.
