# Feature Specification: Cinepolis McKinney Showtime Ingestion (Alpha Cinema)

**Feature Branch**: `001-cinepolis-showtime-ingestion`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "There is a local cinema called Cinepolis, specifically their Mckinney location off the 121. I'd like to begin processing their showtimes as the alpha cinema."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Capture current showtimes for the alpha cinema (Priority: P1)

As the operator of this project, I want the system to pull in current movie
showtimes for the Cinepolis McKinney location so that this single cinema can
serve as the proving ground before any other cinema is added.

**Why this priority**: Without reliable ingestion of a single cinema's
showtimes, nothing downstream (recommendations, browsing, etc.) can be built
or validated. This is the foundational slice.

**Independent Test**: Can be fully tested by running the ingestion process
once and confirming that a set of showtimes attributed to the Cinepolis
McKinney cinema (movie title, date, start time) is available in storage
afterward.

**Acceptance Scenarios**:

1. **Given** the Cinepolis McKinney location is configured as the alpha
   cinema, **When** an ingestion run executes, **Then** the system stores a
   showtime record for every movie/session currently published by that
   cinema.
2. **Given** an ingestion run has already populated showtimes, **When** a
   second ingestion run executes against unchanged source data, **Then** no
   duplicate showtime records are created.

---

### User Story 2 - Keep showtimes current as they change (Priority: P2)

As the operator, I want previously ingested showtimes to be refreshed on a
recurring basis so that added sessions, cancellations, and time changes are
reflected without manual intervention.

**Why this priority**: Showtimes change daily (new days open up, sessions
sell out or get cancelled). Stale data would make the alpha cinema pilot
untrustworthy for anything built on top of it.

**Independent Test**: Can be fully tested by altering the set of showtimes
available from the source between two ingestion runs and confirming stored
data reflects additions and removals after the second run.

**Acceptance Scenarios**:

1. **Given** a showtime existed in a prior ingestion run, **When** that
   showtime is no longer published by the source on a later run, **Then**
   the system marks or removes the corresponding stored record so stale
   showtimes are not surfaced.
2. **Given** a new showtime is published by the source that did not exist
   in the prior run, **When** ingestion runs again, **Then** the new
   showtime appears in storage.

---

### User Story 4 - View ingested showtimes (Priority: P2)

As the operator, I want a simple, human-readable listing of the showtimes
that have been ingested for the Cinepolis McKinney cinema, so I can
visually verify the data is accurate without inspecting raw storage.

**Why this priority**: A minimal view is the fastest way to build
confidence that ingestion is producing correct, usable data during the
alpha pilot.

**Independent Test**: Can be fully tested by ingesting a known set of
showtimes and confirming the listing view displays each one with correct
movie title, date, start time, and format.

**Acceptance Scenarios**:

1. **Given** showtimes have been ingested for the Cinepolis McKinney
   cinema, **When** the operator opens the listing view, **Then** each
   ingested showtime is displayed with its movie title, date, start time,
   and format.
2. **Given** no showtimes have been ingested yet, **When** the operator
   opens the listing view, **Then** it clearly indicates there is no data
   yet rather than appearing broken or blank without explanation.

---

### User Story 3 - Verify ingestion health for the alpha cinema (Priority: P3)

As the operator, I want visibility into whether each ingestion run
succeeded and how many showtimes it captured, so I can trust the pipeline
before adding more cinemas.

**Why this priority**: This is a single-cinema pilot specifically to build
confidence in the pipeline; being able to verify it worked (or diagnose why
it didn't) is essential to deciding when to expand to additional cinemas.

**Independent Test**: Can be fully tested by triggering an ingestion run and
confirming a human-readable record (log or summary) exists showing the run
outcome and showtime count, including for a run where the source is
unreachable or returns no data.

**Acceptance Scenarios**:

1. **Given** an ingestion run completes successfully, **When** the operator
   checks the run outcome, **Then** it shows the number of showtimes
   captured for the Cinepolis McKinney cinema.
2. **Given** an ingestion run fails (e.g., source unreachable), **When** the
   operator checks the run outcome, **Then** the failure is clearly
   distinguishable from a successful run that simply found zero showtimes.

---

### Edge Cases

- What happens when the Cinepolis McKinney source publishes no showtimes at
  all for a given run (e.g., off-hours, temporary closure)?
- How does the system handle a showtime whose start time or format changes
  between ingestion runs without the showtime being removed and re-added?
- What happens when the source is temporarily unreachable mid-run (partial
  data retrieved)?
- How does the system handle a movie title that is formatted or spelled
  inconsistently between ingestion runs for what is otherwise the same
  session?
- What happens when no ticket-purchase URL can be determined for a
  showtime at all (e.g., the source's API doesn't expose one, or its
  construction can't be reverse-engineered)? Per FR-011, the showtime is
  still captured normally with the URL simply absent — this must never
  block ingestion of the showtime itself.

## Clarifications

### Session 2026-07-22

- Q: What source should the system retrieve Cinepolis McKinney showtimes from? → A: Cinepolis' own website for the McKinney location.
- Q: How often should the system re-run ingestion to keep showtimes current? → A: A configurable interval, recommended default every 2-4 hours.
- Q: Should this feature include a user-facing view of ingested showtimes, or is it backend ingestion/storage only? → A: Include a minimal view — a simple listing of ingested showtimes.
- Q (raised via feature 004's clarification session): feature 004 (showtime notifications) needs a direct ticket-purchase link per showtime, which this feature does not currently capture — should this feature be extended to capture one? → A: Yes — capture a per-showing ticket/booking URL when the source provides one. The exact URL is not yet confirmed to exist in Cinepolis' GraphQL response (the current `showingsForDate` query only returns `id`/`time`/`screenId`/`movie{id,name}`) and Cinepolis' site is Cloudflare-protected, so reverse-engineering the real booking-page URL pattern (e.g., from the showing's `id`) is deferred to this feature's own research/planning update — not resolved in this clarification session.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST treat the Cinepolis McKinney location as the
  sole ("alpha") cinema for showtime ingestion in this phase; no other
  cinema is in scope.
- **FR-002**: The system MUST retrieve currently published showtimes
  directly from Cinepolis' own website for the McKinney location (no
  third-party aggregator or partner API in this phase).
- **FR-003**: For each showtime, the system MUST capture at minimum: movie
  title, showing date, start time, and format/auditorium type when the
  source provides it (e.g., standard, VIP, 4DX).
- **FR-004**: The system MUST persist ingested showtimes in a way that
  downstream features (e.g., future recommendation logic) can query them.
- **FR-005**: The system MUST associate every stored showtime with the
  Cinepolis McKinney cinema identity, so the data model supports additional
  cinemas being added later without redesign.
- **FR-006**: The system MUST avoid creating duplicate records for the same
  showtime across repeated ingestion runs.
- **FR-007**: The system MUST re-run ingestion on a recurring schedule, at
  a configurable interval (recommended default: every 2-4 hours), to keep
  showtimes reasonably current.
- **FR-008**: The system MUST reconcile each ingestion run's results against
  previously stored showtimes, so showtimes no longer published by the
  source are marked stale or removed, and newly published showtimes are
  added.
- **FR-009**: The system MUST record, for every ingestion run, whether it
  succeeded or failed and how many showtimes were captured, distinguishing
  "zero showtimes found" from "run failed."
- **FR-010**: The system MUST provide a minimal, human-readable view that
  lists ingested showtimes for the Cinepolis McKinney cinema (movie title,
  date, start time, format), so ingested data can be visually verified
  without inspecting raw storage.
- **FR-011**: The system MUST capture a direct ticket-purchase URL for
  each showtime when the source makes one available, so downstream
  features (e.g., feature 004's notifications) can link the operator
  straight to booking that showing. If no such URL can be determined for
  a showtime, the system MUST leave it absent rather than fabricating or
  guessing one (mirrors FR-003's "when the source provides it" pattern
  for format).

### Key Entities

- **Cinema**: Represents a physical theater location. For this phase, the
  only instance is Cinepolis McKinney (off Highway 121). Attributes include
  name, location/address, and an identifier future cinemas will also use.
- **Showtime**: Represents a single scheduled screening at a cinema.
  Attributes include the associated cinema, movie title, date, start time,
  format/auditorium type, and (per FR-011) an optional direct
  ticket-purchase URL when the source provides one. Each showtime must be
  distinguishable from others for the same movie on the same day (e.g.,
  by date + start time + format).
- **Ingestion Run**: Represents one execution of the showtime-fetching
  process. Attributes include start time, outcome (success/failure), and
  count of showtimes captured or changed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An ingestion run against the Cinepolis McKinney cinema
  captures showtimes for 100% of the movies/sessions that cinema currently
  publishes, verified by manual spot-check against the cinema's own posted
  schedule.
- **SC-002**: Running ingestion repeatedly against unchanged source data
  produces zero duplicate showtime records.
- **SC-003**: A showtime that disappears from the source is no longer
  presented as active within one ingestion cycle of its removal.
- **SC-004**: The operator can determine, within one minute of checking,
  whether the most recent ingestion run succeeded and how many showtimes it
  captured — without needing to inspect raw data.
- **SC-006**: The operator can view the current list of ingested showtimes
  for the Cinepolis McKinney cinema, with correct movie title, date, start
  time, and format, without needing to inspect raw storage.
- **SC-005**: The pipeline's data model requires no redesign when a second
  cinema is later added — `Showtime`/`IngestionRun` are already scoped
  per-`Cinema`. Onboarding a new cinema does require a small, contained
  code change to `main.py`'s bootstrap (which currently hardcodes one
  `Cinema` row), not a redesign of the ingestion/storage/view logic
  itself.

## Assumptions

- The Cinepolis McKinney location referenced is the one located near
  Highway 121 in McKinney, Texas, and is uniquely identifiable as a single
  physical cinema.
- Only current and near-term future showtimes are in scope; historical
  (past) showtimes do not need to be retained or backfilled.
- This feature is explicitly a pilot ("alpha") intended to validate the
  ingestion approach before additional cinemas are onboarded; it is not
  expected to support multiple cinemas simultaneously yet, though the data
  model should not preclude that.
- No user authentication or personalization is involved in this feature —
  the minimal listing view is for the operator to verify ingested data, not
  an end-user-facing recommendation experience (which is assumed to be a
  separate, later feature).
