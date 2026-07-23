# Feature Specification: Angelika Film Center Dallas Showtime Ingestion Source

**Feature Branch**: `008-angelika-dallas-source`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Onboard a new cinema https://angelikafilmcenter.com/dallas"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingest upcoming showtimes from Angelika Film Center Dallas (Priority: P1)

As the operator of the cinema recommendation system, I want the system to ingest upcoming showtimes from the Angelika Film Center Dallas public site (https://angelikafilmcenter.com/dallas) so that screenings at this venue are included in our showtime inventory alongside the other onboarded cinemas.

**Why this priority**: Core functionality. Without pulling showtimes into inventory, Angelika Dallas screenings cannot be surfaced or recommended.

**Independent Test**: Can be verified by triggering an ingestion run for the Angelika Dallas source and confirming that scheduled upcoming screenings (movie title, screening date, start time, and ticket/detail link) are populated in stored records.

**Acceptance Scenarios**:

1. **Given** the Angelika Dallas site has upcoming published showtimes, **When** an ingestion process runs for this source, **Then** all scheduled screenings for future dates/times are added to the system inventory.
2. **Given** an ingestion run has completed for Angelika Dallas, **When** a subsequent ingestion run occurs with no changes on the source, **Then** existing screening records are retained without creating duplicate entries.

---

### User Story 2 - Capture screening formats and ticket links (Priority: P2)

As a moviegoer browsing Angelika Dallas showtimes, I want each ingested screening to capture presentation attributes (such as standard digital, 3D, or special-event formats) and a direct ticketing link so that I know how the film is being shown and can easily purchase tickets.

**Why this priority**: Angelika is an arthouse/indie-leaning chain that also runs limited-release and special-event screenings; capturing format and ticket link gives meaningfully better value than a bare title/time listing.

**Independent Test**: Can be verified by ingesting a listing tagged with a non-default format (e.g., a special event or alternate presentation) and confirming that the format attribute and ticket link are correctly captured on the ingested screening record.

**Acceptance Scenarios**:

1. **Given** a showtime listing specifies a non-default presentation format, **When** the screening is ingested, **Then** the format is explicitly associated with the stored screening record.
2. **Given** a showtime listing contains a direct ticket purchase link, **When** the screening is ingested, **Then** the URL is saved with the screening record.

---

### User Story 3 - Synchronize schedule updates and cancellations (Priority: P3)

As the operator, I want previously ingested Angelika Dallas showtimes to stay synchronized with source updates, so that cancelled screenings or rescheduled times are accurately reflected in the system.

**Why this priority**: Theater schedules shift regularly (added showtimes, sold-out swaps, cancellations); keeping data current prevents recommending stale or invalid showtimes.

**Independent Test**: Can be verified by running ingestion after a schedule modification (e.g., time change or removed screening) and confirming that the stored screening is updated or marked inactive accordingly.

**Acceptance Scenarios**:

1. **Given** a previously ingested screening is removed or canceled on the source site, **When** a new ingestion run completes, **Then** the screening is marked inactive or removed from active showtime inventory.
2. **Given** a screening time or title is updated on the source site, **When** a new ingestion run completes, **Then** the stored record is updated to match the latest details.

---

### Edge Cases

- What happens when the site requires client-side rendering (JavaScript execution) to reveal showtimes, rather than serving them in static HTML?
- How does the system handle non-film events listed on the site (e.g., Q&As, special engagements, rentals)?
- How does the system handle temporary network unavailability, anti-bot protections, or layout changes on the Angelika Dallas site?
- What happens when a showtime listing spans multiple screens/auditoriums for the same film at the same time?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST fetch and parse upcoming showtimes from the Angelika Film Center Dallas public site (`https://angelikafilmcenter.com/dallas`).
- **FR-002**: System MUST extract essential screening details for each listing: film title, screening date, start time, venue identifier, and detail/ticket URL.
- **FR-003**: System MUST identify and store presentation format indicators (e.g., 3D, special event) when specified in the listing or event details.
- **FR-004**: System MUST assign all ingested showtimes to a distinct Angelika Film Center Dallas venue record.
- **FR-005**: System MUST prevent duplicate screening records when re-ingesting the same schedule.
- **FR-006**: System MUST update or deactivate existing screening records when changes or cancellations occur on the source site.
- **FR-007**: System MUST log operational progress and errors clearly during Angelika Dallas ingestion runs to enable operational monitoring.
- **FR-008**: System MUST distinguish film screening events from non-screening venue events (or tag non-film events appropriately) to maintain high data quality for movie recommendations.

### Key Entities

- **Angelika Dallas Source**: Represents the cinema venue source configuration (name, location, base URL, timezone).
- **Angelika Dallas Screening**: Represents a specific scheduled film projection or event session (title, date, start time, venue, format tags, detail link, active status).
- **Screening Format**: Represents presentation attributes associated with a screening (e.g., Standard, 3D, Special Event).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of published upcoming film screenings on the Angelika Dallas site are successfully ingested during a scheduled run.
- **SC-002**: Re-ingestions of unchanged source data result in zero duplicate screening records.
- **SC-003**: Screening presentation formats are captured accurately for at least 95% of listings that specify format details on the source site.
- **SC-004**: Single-run ingestion of Angelika Dallas showtimes completes within 30 seconds under normal network conditions.

## Assumptions

- The Angelika Dallas site at `https://angelikafilmcenter.com/dallas` is publicly accessible without user authentication or paywalls.
- Angelika Dallas showtimes are scheduled in the Central Time zone (America/Chicago), consistent with its Dallas, TX location.
- Non-film events (Q&As, rentals, special engagements) on the site can either be ingested with an appropriate event classification or filtered if irrelevant to film recommendations.
- The exact rendering technology of the source site (static HTML vs. JavaScript-rendered SPA vs. third-party ticketing widget) is undetermined at spec time and will be investigated during planning; this spec is written technology-agnostic per FR-001/FR-002.
- Standard web crawling and page parsing practices apply in compliance with website terms and reasonable access rates.
