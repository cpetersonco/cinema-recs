# Feature Specification: Cinemark West Plano XD and ScreenX Showtime Ingestion Source

**Feature Branch**: `012-cinemark-west-plano-source`

**Created**: 2026-07-23

**Status**: Draft

**Input**: User description: "Onboard this local cinemark location. I'm specifically interested in their 70mm/special presentations. https://www.cinemark.com/theatres/tx-plano/cinemark-west-plano-xd-and-screenx"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingest upcoming showtimes from Cinemark West Plano (Priority: P1)

As the operator of the cinema recommendation system, I want the system to ingest upcoming showtimes from Cinemark West Plano XD and ScreenX (`https://www.cinemark.com/theatres/tx-plano/cinemark-west-plano-xd-and-screenx`) so that screenings at this venue are included in our showtime inventory alongside the other onboarded cinemas.

**Why this priority**: Core functionality. Without pulling showtimes into inventory, nothing else in this feature has anything to operate on.

**Independent Test**: Can be verified by triggering an ingestion run for the Cinemark West Plano source and confirming that scheduled upcoming screenings (movie title, screening date, start time, and ticket/detail link) are populated in stored records.

**Acceptance Scenarios**:

1. **Given** the Cinemark West Plano site has upcoming published showtimes, **When** an ingestion process runs for this source, **Then** all scheduled screenings for future dates/times within the site's published scheduling window are added to the system inventory.
2. **Given** an ingestion run has completed for Cinemark West Plano, **When** a subsequent ingestion run occurs with no changes on the source, **Then** existing screening records are retained without creating duplicate entries.

---

### User Story 2 - Identify 70mm and other special presentation formats (Priority: P1)

As a moviegoer who specifically cares about premium and special presentation formats at this venue, I want each ingested screening to capture its presentation format — including 70mm, XD, ScreenX, D-BOX, and 3D — so that I can find and prioritize 70mm and other special screenings distinct from standard showings.

**Why this priority**: This is the user's explicit, stated motivation for onboarding this venue. A listing without accurate format tagging (particularly 70mm) does not deliver the value the user asked for, so this is equal in priority to basic ingestion, not a nice-to-have.

**Independent Test**: Can be verified by ingesting a listing that includes a 70mm showtime (e.g., "The Odyssey" or another film scheduled in the 70mm format) and confirming the format is stored as a distinct, filterable attribute of that screening, separate from standard/XD/ScreenX/3D showings of the same film.

**Acceptance Scenarios**:

1. **Given** a film has multiple showtimes in different formats (e.g., Standard, XD, 70mm) at Cinemark West Plano, **When** the screenings are ingested, **Then** each showtime is stored with its own correct format tag rather than being collapsed into a single undifferentiated listing.
2. **Given** a showtime is presented in 70mm, **When** it is ingested, **Then** the screening record is explicitly identifiable as 70mm (not merely "special" or "premium") so it can be surfaced separately from other formats.
3. **Given** a showtime is presented in ScreenX, XD, D-BOX, or 3D, **When** it is ingested, **Then** the screening record captures that specific format.

---

### User Story 3 - Synchronize schedule updates and cancellations (Priority: P3)

As the operator, I want previously ingested Cinemark West Plano showtimes to stay synchronized with source updates, so that cancelled screenings or rescheduled times are accurately reflected in the system.

**Why this priority**: Theater schedules shift regularly (added showtimes, sold-out swaps, cancellations, event-only screenings like the Met Opera); keeping data current prevents recommending stale or invalid showtimes. Lower priority than P1s because stale-but-present data is still usable in the short term, whereas missing ingestion or missing format tagging defeats the feature's purpose entirely.

**Independent Test**: Can be verified by running ingestion after a schedule modification (e.g., time change or removed screening) and confirming that the stored screening is updated or marked inactive accordingly.

**Acceptance Scenarios**:

1. **Given** a previously ingested screening is removed or canceled on the source site, **When** a new ingestion run completes, **Then** the screening is marked inactive or removed from active showtime inventory.
2. **Given** a screening time, title, or format is updated on the source site, **When** a new ingestion run completes, **Then** the stored record is updated to match the latest details.

---

### Edge Cases

- What happens when the site requires client-side rendering (JavaScript execution) to reveal showtimes, rather than serving them fully in static HTML?
- How does the system handle non-film events listed on the site (e.g., Studio Ghibli Fest, Met Opera broadcasts, anniversary re-releases, subtitled international screenings)?
- How does the system handle a film showing in more than one special format at overlapping times (e.g., simultaneous XD and ScreenX showtimes of the same title)?
- What happens when the site's schedule navigation only exposes a limited future window (e.g., a rolling few weeks) rather than the venue's full published calendar?
- How does the system handle temporary network unavailability, anti-bot protections, or layout changes on the Cinemark site?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST fetch and parse upcoming showtimes from the Cinemark West Plano XD and ScreenX public site (`https://www.cinemark.com/theatres/tx-plano/cinemark-west-plano-xd-and-screenx`).
- **FR-002**: System MUST extract essential screening details for each listing: film title, screening date, start time, venue identifier, and detail/ticket URL.
- **FR-003**: System MUST identify and store the presentation format for every screening, distinguishing at minimum: Standard, 70mm, XD, ScreenX, D-BOX, and RealD 3D.
- **FR-004**: System MUST tag 70mm screenings with a distinct, unambiguous format value (not grouped under a generic "special presentation" label) so they can be filtered and surfaced independently of other formats.
- **FR-005**: System MUST assign all ingested showtimes to a distinct Cinemark West Plano venue record.
- **FR-006**: System MUST prevent duplicate screening records when re-ingesting the same schedule.
- **FR-007**: System MUST update or deactivate existing screening records when changes or cancellations occur on the source site.
- **FR-008**: System MUST log operational progress and errors clearly during Cinemark West Plano ingestion runs to enable operational monitoring.
- **FR-009**: System MUST distinguish film screening events from non-screening venue events (e.g., opera broadcasts, fan festivals) or tag non-film events appropriately, to maintain high data quality for movie recommendations.
- **FR-010**: System MUST capture multiple concurrent format offerings of the same film (e.g., the same title showing in both Standard and 70mm at different times) as separate, individually identifiable screening records.

### Key Entities

- **Cinemark West Plano Source**: Represents the cinema venue source configuration (name, location, base URL, timezone).
- **Cinemark West Plano Screening**: Represents a specific scheduled film projection or event session (title, date, start time, venue, format tag, detail/ticket link, active status).
- **Screening Format**: Represents the presentation attribute associated with a screening — Standard, 70mm, XD, ScreenX, D-BOX, or RealD 3D — with 70mm treated as a first-class, distinctly identifiable value given the user's specific interest in it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of published upcoming film screenings on the Cinemark West Plano site are successfully ingested during a scheduled run.
- **SC-002**: Re-ingestions of unchanged source data result in zero duplicate screening records.
- **SC-003**: 100% of screenings presented in 70mm are correctly and distinctly tagged as such (not merged with other formats or omitted).
- **SC-004**: At least 95% of listings specifying any presentation format (XD, ScreenX, D-BOX, 3D) are captured with the correct format attribute.
- **SC-005**: Single-run ingestion of Cinemark West Plano showtimes completes within 30 seconds under normal network conditions.

## Assumptions

- The Cinemark West Plano page is publicly accessible without login, though it may render its schedule via client-side JavaScript; the exact rendering technology is undetermined at spec time and will be investigated during planning, per FR-001/FR-002 being written technology-agnostic.
- Cinemark West Plano showtimes are scheduled in the Central Time zone (America/Chicago), consistent with its Plano, TX location.
- "70mm" refers to Cinemark's film-format presentations (e.g., "The Odyssey 70mm" as currently listed on the site) and is treated as its own format category distinct from XD, ScreenX, D-BOX, and 3D, which are separate premium formats at this venue.
- Non-film events (Met Opera broadcasts, fan festivals, anniversary re-releases) can either be ingested with an appropriate event classification or filtered if irrelevant to film recommendations, consistent with the precedent set for other onboarded venues.
- Standard web crawling and page parsing practices apply in compliance with website terms and reasonable access rates.
