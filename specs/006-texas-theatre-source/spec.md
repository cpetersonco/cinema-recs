# Feature Specification: Texas Theatre Showtime Ingestion Source

**Feature Branch**: `006-texas-theatre-source`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "I want to implement a new movie source https://thetexastheatre.com/calendar"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingest upcoming showtimes from Texas Theatre calendar (Priority: P1)

As the operator of the cinema recommendation system, I want the system to ingest upcoming showtimes from the Texas Theatre public calendar (https://thetexastheatre.com/calendar) so that screenings at this venue are included in our showtime inventory.

**Why this priority**: Core functionality. Without pulling calendar events into our showtime inventory, Texas Theatre screenings cannot be surfaced or recommended.

**Independent Test**: Can be verified by triggering an ingestion run for the Texas Theatre source and confirming that scheduled upcoming screenings (movie title, screening date, start time, and event link) are populated in stored records.

**Acceptance Scenarios**:

1. **Given** the Texas Theatre calendar has upcoming published screenings, **When** an ingestion process runs for this source, **Then** all scheduled screenings for future dates/times are added to the system inventory.
2. **Given** an ingestion run has completed for Texas Theatre, **When** a subsequent ingestion run occurs with no changes on the calendar, **Then** existing screening records are retained without creating duplicate entries.

---

### User Story 2 - Capture film screening formats and ticket links (Priority: P2)

As a moviegoer browsing Texas Theatre showtimes, I want each ingested screening to capture available presentation attributes (such as 35mm, 70mm, 16mm, or digital) and direct ticketing links so that I know the presentation format and can easily purchase tickets.

**Why this priority**: Texas Theatre is renowned for specialty film formats (35mm, 70mm, archival prints). Preserving projection format and direct ticket URLs provides significant value over generic showtime listings.

**Independent Test**: Can be verified by ingesting a calendar entry tagged with a specialty format (e.g., 35mm screening) and confirming that format attributes and ticket links are correctly captured on the ingested screening record.

**Acceptance Scenarios**:

1. **Given** a calendar listing specifies a specialty screening format (e.g. 35mm or 70mm), **When** the screening is ingested, **Then** the projection format is explicitly associated with the stored screening record.
2. **Given** a calendar listing contains a direct ticket purchase or detail page link, **When** the screening is ingested, **Then** the URL is saved with the screening record.

---

### User Story 3 - Synchronize calendar updates and cancellations (Priority: P3)

As the operator, I want previously ingested Texas Theatre showtimes to stay synchronized with calendar updates, so that cancelled screenings or rescheduled times are accurately reflected in the system.

**Why this priority**: Rep houses and indie theaters frequently update showtime schedules or cancel/reschedule events. Keeping data current prevents showing stale or invalid options.

**Independent Test**: Can be verified by running ingestion after a calendar modification (e.g., time change or removed screening) and confirming that the stored screening is updated or marked inactive accordingly.

**Acceptance Scenarios**:

1. **Given** a previously ingested screening is removed or canceled on the Texas Theatre calendar, **When** a new ingestion run completes, **Then** the screening is marked inactive or removed from active showtime inventory.
2. **Given** a screening time or title is updated on the Texas Theatre calendar, **When** a new ingestion run completes, **Then** the stored record is updated to match the latest details.

---

### Edge Cases

- What happens when the calendar page contains multi-day events or marathons with unspecified individual start times?
- How does the system handle non-film events listed on the calendar (e.g., live comedy, music concerts, behind-the-screen shows)?
- How does the system handle temporary network unavailability or layout changes on the Texas Theatre website?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST fetch and parse upcoming showtime and screening events from the Texas Theatre public calendar (`https://thetexastheatre.com/calendar`).
- **FR-002**: System MUST extract essential screening details for each listing: film/event title, screening date, start time, venue identifier, and detail/ticket URL.
- **FR-003**: System MUST identify and store specialty projection format indicators (e.g., 35mm, 70mm, 16mm, 4K digital) when specified in the calendar listing or event details.
- **FR-004**: System MUST assign all ingested showtimes to the Texas Theatre venue record.
- **FR-005**: System MUST prevent duplicate screening records when re-ingesting the same calendar schedule.
- **FR-006**: System MUST update or deactivate existing screening records when changes or cancellations occur on the source calendar.
- **FR-007**: System MUST log operational progress and errors clearly during Texas Theatre calendar ingestion runs to enable operational monitoring.
- **FR-008**: System MUST distinguish film screening events from non-screening venue events (or tag non-film events appropriately) to maintain high data quality for movie recommendations.

### Key Entities

- **Texas Theatre Source**: Represents the cinema venue source configuration (name, location, base URL, timezone).
- **Texas Theatre Screening**: Represents a specific scheduled film projection or event session (title, date, start time, venue, format tags, detail link, active status).
- **Screening Format**: Represents presentation attributes associated with a screening (e.g., 35mm, 70mm, 16mm, Digital, Q&A session).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of published upcoming film screenings on the Texas Theatre calendar page are successfully ingested during a scheduled run.
- **SC-002**: Re-ingestions of unchanged calendar data result in zero duplicate screening records.
- **SC-003**: Screening projection formats (35mm, 70mm, 16mm) are captured accurately for at least 95% of listings that specify format details on the calendar.
- **SC-004**: Single-run ingestion of Texas Theatre calendar events completes within 30 seconds under normal network conditions.

## Assumptions

- The Texas Theatre calendar at `https://thetexastheatre.com/calendar` is publicly accessible without user authentication or paywalls.
- Texas Theatre showtimes are scheduled in the Central Time zone (America/Chicago).
- Non-film events (concerts, podcasts, live comedy) on the calendar can either be ingested with an appropriate event classification or filtered if irrelevant to film recommendations.
- Standard web crawling and page parsing practices apply in compliance with website terms and reasonable access rates.
