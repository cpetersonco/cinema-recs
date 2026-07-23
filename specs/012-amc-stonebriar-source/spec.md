# Feature Specification: AMC Stonebriar 24 Showtime Ingestion Source

**Feature Branch**: `012-amc-stonebriar-source`

**Created**: 2026-07-23

**Status**: Draft

**Input**: User description: "onboard this AMC location as a data source. https://www.amctheatres.com/movie-theatres/dallas-ft-worth/amc-stonebriar-24/showtime"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingest upcoming showtimes from AMC Stonebriar 24 (Priority: P1)

As the operator of the cinema recommendation system, I want the system to ingest upcoming showtimes from the AMC Stonebriar 24 public site (https://www.amctheatres.com/movie-theatres/dallas-ft-worth/amc-stonebriar-24/showtime) so that screenings at this venue are included in our showtime inventory alongside the other onboarded cinemas.

**Why this priority**: Core functionality. Without pulling showtimes into inventory, AMC Stonebriar 24 screenings cannot be surfaced or recommended.

**Independent Test**: Can be verified by triggering an ingestion run for the AMC Stonebriar 24 source and confirming that scheduled upcoming screenings (movie title, screening date, start time, and ticket/detail link) are populated in stored records.

**Acceptance Scenarios**:

1. **Given** the AMC Stonebriar 24 site has upcoming published showtimes, **When** an ingestion process runs for this source, **Then** all scheduled screenings for future dates/times are added to the system inventory.
2. **Given** an ingestion run has completed for AMC Stonebriar 24, **When** a subsequent ingestion run occurs with no changes on the source, **Then** existing screening records are retained without creating duplicate entries.

---

### User Story 2 - Capture screening formats, auditorium, and ticket links (Priority: P2)

As a moviegoer browsing AMC Stonebriar 24 showtimes, I want each ingested screening to capture presentation attributes (such as standard digital, IMAX, Dolby Cinema, RealD 3D, Dine-In, or other premium large-format/PLF indicators) and a direct ticketing link so that I know how the film is being shown and can easily purchase tickets.

**Why this priority**: AMC Stonebriar 24 is a large-format multiplex offering multiple premium presentation types for the same title; capturing format and ticket link gives meaningfully better value than a bare title/time listing and lets recommendations distinguish, e.g., IMAX from standard screenings.

**Independent Test**: Can be verified by ingesting a listing tagged with a non-default format (e.g., IMAX or Dolby Cinema) and confirming that the format attribute and ticket link are correctly captured on the ingested screening record.

**Acceptance Scenarios**:

1. **Given** a showtime listing specifies a non-default presentation format, **When** the screening is ingested, **Then** the format is explicitly associated with the stored screening record.
2. **Given** a showtime listing contains a direct ticket purchase link, **When** the screening is ingested, **Then** the URL is saved with the screening record.

---

### User Story 3 - Synchronize schedule updates and cancellations (Priority: P3)

As the operator, I want previously ingested AMC Stonebriar 24 showtimes to stay synchronized with source updates, so that cancelled screenings or rescheduled times are accurately reflected in the system.

**Why this priority**: Multiplex schedules shift regularly (added showtimes, sold-out swaps, cancellations, rolling releases); keeping data current prevents recommending stale or invalid showtimes.

**Independent Test**: Can be verified by running ingestion after a schedule modification (e.g., time change or removed screening) and confirming that the stored screening is updated or marked inactive accordingly.

**Acceptance Scenarios**:

1. **Given** a previously ingested screening is removed or canceled on the source site, **When** a new ingestion run completes, **Then** the screening is marked inactive or removed from active showtime inventory.
2. **Given** a screening time or title is updated on the source site, **When** a new ingestion run completes, **Then** the stored record is updated to match the latest details.

---

### Edge Cases

- What happens when the site requires client-side rendering (JavaScript execution) or an internal API call to reveal showtimes, rather than serving them in static HTML?
- How does the system handle anti-bot protections (e.g., Cloudflare or similar), given other onboarded sources have required TLS-impersonation workarounds for such protections?
- How does the system handle showtimes that are sold out or not yet on sale (ticket link unavailable) versus openly bookable ones?
- What happens when a single film has multiple simultaneous showtimes across different auditoriums/formats at the same start time?
- How does the system handle the site showing only a limited number of days (e.g., today + N days) rather than the full future window used by other sources?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST fetch and parse upcoming showtimes from the AMC Stonebriar 24 public site (`https://www.amctheatres.com/movie-theatres/dallas-ft-worth/amc-stonebriar-24/showtime`).
- **FR-002**: System MUST extract essential screening details for each listing: film title, screening date, start time, venue identifier, and detail/ticket URL.
- **FR-003**: System MUST identify and store presentation format indicators (e.g., IMAX, Dolby Cinema, RealD 3D, Dine-In, standard) when specified in the listing.
- **FR-004**: System MUST assign all ingested showtimes to a distinct AMC Stonebriar 24 venue record.
- **FR-005**: System MUST prevent duplicate screening records when re-ingesting the same schedule.
- **FR-006**: System MUST update or deactivate existing screening records when changes or cancellations occur on the source site.
- **FR-007**: System MUST log operational progress and errors clearly during AMC Stonebriar 24 ingestion runs to enable operational monitoring.
- **FR-008**: System MUST fall back to TMDB rating data when a film's rating is unavailable from the AMC listing, consistent with existing rating-enrichment behavior for other sources.

### Key Entities

- **AMC Stonebriar 24 Source**: Represents the cinema venue source configuration (name, location, base URL, timezone).
- **AMC Stonebriar 24 Screening**: Represents a specific scheduled film projection (title, date, start time, venue, format tags, detail/ticket link, active status).
- **Screening Format**: Represents presentation attributes associated with a screening (e.g., Standard, IMAX, Dolby Cinema, RealD 3D, Dine-In).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of published upcoming film screenings on the AMC Stonebriar 24 site are successfully ingested during a scheduled run.
- **SC-002**: Re-ingestions of unchanged source data result in zero duplicate screening records.
- **SC-003**: Screening presentation formats are captured accurately for at least 95% of listings that specify format details on the source site.
- **SC-004**: Single-run ingestion of AMC Stonebriar 24 showtimes completes within 30 seconds under normal network conditions.

## Assumptions

- The AMC Stonebriar 24 showtime page is publicly accessible without user authentication, though it may require anti-bot or JavaScript-rendering workarounds similar to other onboarded sources.
- AMC Stonebriar 24 showtimes are scheduled in the Central Time zone (America/Chicago), consistent with its Frisco, TX (Dallas-Ft. Worth) location.
- The exact rendering technology of the source site (static HTML vs. JavaScript-rendered SPA vs. internal data API) is undetermined at spec time and will be investigated during planning; this spec is written technology-agnostic per FR-001/FR-002.
- Standard web crawling and page parsing practices apply in compliance with website terms and reasonable access rates.
