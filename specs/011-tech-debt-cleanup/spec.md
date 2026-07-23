# Feature Specification: Tech Debt Cleanup — Cinema Routing, Deprecated APIs, Startup Coverage

**Feature Branch**: `011-tech-debt-cleanup`

**Created**: 2026-07-23

**Status**: Draft

**Input**: User description: "Create a feature to address the above tech debt" (referring to the
architectural overview delivered in this session, which identified 7 findings across the
codebase)

## User Scenarios & Testing *(mandatory)*

<!--
  This feature addresses the 3 highest-priority findings from the architectural
  review, in the order the review itself recommended tackling them:

  1. Cinema-to-scraper routing is done by string-matching the cinema's name/URL
     against each known source, with an unrecognized source silently falling
     through to the Cinepolis scraper instead of failing loudly.
  2. The app calls a deprecated datetime API in 10 places, which currently
     works but is scheduled for removal in a future Python version and
     already produces warning noise on every test run.
  3. The code that wires the whole app together at startup (which cinemas
     get configured, how the CLI entry point behaves) has no test coverage
     at all, unlike every other module in the app.

  The other 4 findings from the review (advisory-only lint debt, no
  dependency-update automation, growing module sizes, ad-hoc migrations)
  were explicitly assessed as low-urgency/no-action-needed-yet and are out
  of scope here — see Assumptions.
-->

### User Story 1 - Fail loudly on an unrecognized cinema source instead of silently misrouting (Priority: P1)

As the operator, when a cinema's configured source doesn't match a scraper
the app actually knows how to handle, I want the app to fail with a clear
error identifying the problem, rather than silently sending that cinema's
ingestion to the wrong scraper and producing confusing or garbage results.

**Why this priority**: This is the finding with the highest risk-to-effort
ratio identified in the review — a scraper mismatch currently fails
silently (or worse, "succeeds" with wrong data) instead of surfacing as an
obvious, diagnosable error. It's also the prerequisite for the other two
cinema sources' configuration to stop being hardcoded in a way that can't
be verified.

**Independent Test**: Can be fully tested by configuring a cinema whose
source doesn't match any known scraper and triggering an ingestion run for
it, then confirming the run fails with a clear, specific error message
naming the problem — rather than an ingestion run that "succeeds" using
the wrong source's scraper.

**Acceptance Scenarios**:

1. **Given** a cinema configured with a source the app recognizes (one of
   the three currently-supported sources), **When** an ingestion run
   executes for it, **Then** the correct scraper for that source runs, with
   no change in behavior from today.
2. **Given** a cinema configured with a source the app does not recognize,
   **When** an ingestion run executes for it, **Then** the run fails
   immediately with a clear error identifying that the cinema's source
   isn't recognized, and does not fall back to using any other source's
   scraper.
3. **Given** the three currently-supported cinemas, **When** the app starts
   up, **Then** each one's source is explicitly and unambiguously
   identified as one of the app's known source types, not inferred by
   matching text in its name or URL.

---

### User Story 2 - Stop relying on a deprecated timestamp API (Priority: P2)

As the maintainer, I want the app to stop calling the deprecated UTC
timestamp function so that the app keeps working without warnings on
future versions of its runtime, and so real warning output isn't buried
under repeated deprecation noise every time the app or its tests run.

**Why this priority**: Currently harmless (the deprecated function still
works), but it's scheduled for removal in a future runtime version, and
the warning noise it already produces on every test run makes it harder to
notice a genuinely new warning when one appears. Lower priority than
Story 1 because nothing is broken today.

**Independent Test**: Can be fully tested by running the full automated
test suite and confirming no deprecation warnings related to the old
timestamp API appear in the output, while all timestamp-dependent behavior
(record time stamping, ordering, comparisons) continues to work exactly as
before.

**Acceptance Scenarios**:

1. **Given** the full automated test suite, **When** it is run, **Then**
   no deprecation warnings related to the old UTC timestamp API appear in
   the output.
2. **Given** any feature that records or compares timestamps (e.g.
   ingestion run start/finish times, notification records), **When** it is
   exercised, **Then** the recorded/compared values are equivalent to what
   they were before this change — no behavior change, only the
   underlying API call.

---

### User Story 3 - Verify the app's startup wiring is actually correct (Priority: P2)

As the maintainer, I want the code that assembles the app at startup
(which cinemas get configured, how the app responds to its command-line
modes) to be covered by automated tests, so a mistake in that wiring is
caught before it reaches a running deployment instead of only being
discovered by the app misbehaving in production.

**Why this priority**: This is the one place in the app where every other
piece gets connected together, and it's currently the only major piece of
the app with zero test coverage. Lower priority than Story 1/2 because
it's a coverage gap, not an active problem, but doing it now — right after
Story 1 changes that same code — is the cheapest time to add it.

**Independent Test**: Can be fully tested by running the automated test
suite and confirming it includes tests that exercise the startup
assembly logic (which cinemas end up configured, and what happens for
each supported command-line invocation mode) without needing to run the
actual containerized app.

**Acceptance Scenarios**:

1. **Given** the app's normal startup path, **When** the test suite is
   run, **Then** a test confirms all three currently-supported cinemas end
   up configured and ready for ingestion.
2. **Given** each of the app's supported command-line invocation modes,
   **When** the test suite is run, **Then** a test confirms each mode
   performs the operations it's documented to perform (e.g., a one-shot
   ingestion mode runs ingestion without starting the long-running web
   server).

---

### Edge Cases

- What happens to the three cinemas already stored in an existing
  deployment's database, created before this feature under the old
  implicit-routing scheme? They must continue to route to their correct
  scraper after this change with no manual intervention or data loss —
  existing deployments must not require any operator action to keep
  working.
- What happens if two different known source types could both plausibly
  match one cinema's configuration (an ambiguous case)? This must not be
  possible after this feature — a cinema's source must be unambiguous by
  construction, not inferred from text matching that could theoretically
  match more than one pattern.
- What happens to the currently-hardcoded configuration (name, location,
  URL) for the two cinemas that have no environment-variable override
  today? Unchanged by this feature — Story 1 only changes how the app
  decides *which scraper* a cinema uses, not how each cinema's other
  details are configured.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST determine which scraper to use for a cinema
  from an explicit, unambiguous identifier set at the time the cinema is
  configured, not by inspecting or pattern-matching its name or source URL
  at ingestion time.
- **FR-002**: The system MUST support exactly the three source types the
  app currently ships with (Cinepolis-style GraphQL source, Texas
  Theatre-style calendar source, Angelika Dallas-style date-strip source),
  with no behavior change to how any of the three currently ingest.
- **FR-003**: When a cinema's identified source type has no corresponding
  scraper, the system MUST fail that cinema's ingestion run clearly and
  immediately, identifying the unrecognized source type, rather than
  running any other source's scraper against it.
- **FR-004**: The system MUST apply the correct source identifier to
  every cinema already present in an existing deployment's stored data
  without requiring operator action, so upgrading to this feature does not
  break ingestion for previously-configured cinemas.
- **FR-005**: The system MUST NOT call the deprecated UTC timestamp API
  anywhere in the application code.
- **FR-006**: All timestamp-producing and timestamp-comparing behavior
  MUST remain functionally equivalent after removing the deprecated API
  call — no change to what gets recorded, stored, or compared.
- **FR-007**: The system MUST have automated test coverage for its
  startup assembly logic, specifically: which cinemas end up configured
  for ingestion, and what each supported command-line invocation mode
  actually does.
- **FR-008**: This feature MUST NOT change any user-facing behavior,
  scraping logic, ingested data, or the app's external configuration
  surface (environment variables) — it is an internal reliability and
  maintainability change only.

### Key Entities

- **Cinema**: Existing entity (name, location, source URL, creation time).
  Gains an explicit source-type identifier so its associated scraper is
  known by construction rather than inferred; existing rows are given
  their correct identifier as part of this change (FR-004).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of ingestion runs for a cinema with an unrecognized
  source fail with a clear, specific error, with zero cases of an
  unrecognized source's ingestion silently using a different source's
  scraper.
- **SC-002**: The full automated test suite produces zero deprecation
  warnings related to the old timestamp API, down from the warnings
  produced on every run today.
- **SC-003**: 100% of the app's three currently-supported cinemas, and
  100% of its supported command-line invocation modes, are covered by at
  least one automated test.
- **SC-004**: All existing automated tests continue to pass after this
  feature is complete, with no reduction in previously-passing coverage.
- **SC-005**: An operator upgrading an existing deployment to this
  feature observes no disruption to ingestion for any previously-working
  cinema — every cinema keeps ingesting from the same source it did
  before, with no manual data fix-up required.

## Assumptions

- Scope is intentionally limited to the 3 highest-priority findings from
  the architectural review (cinema routing, deprecated timestamp API,
  startup test coverage) — the review's own recommended order of attack.
  The remaining 4 findings are explicitly **out of scope** for this
  feature, per the review's own risk assessment:
  - Advisory-only lint findings (already deliberately non-blocking in CI,
    with that decision documented in the pipeline itself).
  - Lack of automated dependency-update tooling (no active risk today;
    a process/tooling decision independent of application code).
  - Growing size of the scraper/storage modules (acceptable at today's
    scale per the project's simplicity principle; revisit if a 4th
    source or entity type is ever added).
  - Ad-hoc, unversioned database migrations (acceptable at today's scale
    of 2 migrations; revisit if a 3rd becomes necessary).
- "Existing deployment" means the app's single SQLite database file,
  consistent with how prior schema changes in this app have been handled
  (in-place, idempotent migrations run automatically on startup — see
  `storage.py`'s existing migration functions).
- No new environment variables, ports, or volumes are introduced — this
  is purely an internal code-quality change, consistent with FR-008.
