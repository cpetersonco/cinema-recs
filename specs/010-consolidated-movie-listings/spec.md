# Feature Specification: Consolidated Movie Listings with Ticket and Letterboxd Links

**Feature Branch**: `010-consolidated-movie-listings`

**Created**: 2026-07-23

**Status**: Draft

**Input**: User description: "I'd like the UI to only show one listing per movie for each venue. Also the UI should include the showtime link and the rating should link to Letterboxd."

## User Scenarios & Testing *(mandatory)*

<!--
  The listing page (`GET /`) currently renders one table row per active
  showtime record, so a movie with a full week of screenings at one venue
  (now routine since feature 009 fetches each source's full published
  calendar) appears as a wall of near-duplicate rows differing only by
  date/time — the operator has to scan all of them to answer "is this
  worth seeing, and how do I buy a ticket for it." The rating shown is
  also a plain number with no way to see the operator's own trusted
  source (Letterboxd) for it, and the ticket-purchase link that's already
  captured for every showtime isn't shown anywhere in the UI at all.
-->

### User Story 1 - See each movie once per venue instead of once per showing (Priority: P1)

As the operator, I want the listing page to show one row per movie per
venue instead of one row per individual showing, so I can scan what's
playing at a glance instead of wading through a long list of near-
duplicate rows for the same film.

**Why this priority**: This is the core complaint driving the request —
without it, the page's usefulness degrades as more showtimes get
ingested per movie (which is now the normal case after feature 009), and
the other two asks (ticket link, Letterboxd rating link) only matter
once there's one clear row per movie to attach them to.

**Independent Test**: Can be fully tested by ingesting several active
showtimes for the same movie at the same venue (different dates/times)
and confirming the listing page renders exactly one row for that movie
under that venue's section, not one row per showing.

**Acceptance Scenarios**:

1. **Given** a movie has five active showtimes at one venue across the
   next two weeks, **When** the operator loads the listing page,
   **Then** exactly one row appears for that movie in that venue's
   section.
2. **Given** the same movie is also playing at a second venue, **When**
   the operator loads the listing page, **Then** one row appears for
   that movie under each venue's section (one per venue, not one total).
3. **Given** a movie has only one active showtime at a venue, **When**
   the operator loads the listing page, **Then** it still appears as
   exactly one row (no change from today's effective behavior for that
   case).

---

### User Story 2 - Get to the ticket page directly from the listing (Priority: P2)

As the operator, I want each movie's row to link to where I can actually
buy a ticket for it, so I don't have to separately go find the showing
on the venue's own site after deciding it's worth seeing.

**Why this priority**: Useful on its own once User Story 1 gives each
movie a single row to hang a link off of, but it's a convenience on top
of already knowing what's playing — lower priority than fixing the
cluttered listing itself.

**Independent Test**: Can be fully tested by ingesting a showtime with a
captured ticket-purchase link and confirming that link appears on the
movie's row and points to the same URL captured from the source.

**Acceptance Scenarios**:

1. **Given** a movie's consolidated row represents a showtime that has a
   ticket-purchase link captured from the source, **When** the operator
   views the listing, **Then** that link is shown on the row and opens
   the same URL the source provided.
2. **Given** a movie's consolidated row represents a showtime with no
   ticket-purchase link available from the source, **When** the operator
   views the listing, **Then** the row shows no broken/empty link rather
   than an unusable placeholder.

---

### User Story 3 - Jump straight to Letterboxd from the rating (Priority: P2)

As the operator, I want the displayed rating to link to that movie's
Letterboxd page, so I can quickly check reviews/context on the source I
already trust for recommendation decisions, without a separate search.

**Why this priority**: Same tier as the ticket link — a genuine
convenience once a rating is already shown, not something that changes
what information is available today.

**Independent Test**: Can be fully tested by ingesting a movie with a
resolved Letterboxd rating and confirming the rating displayed on its
row links to that movie's Letterboxd page.

**Acceptance Scenarios**:

1. **Given** a movie has a resolved Letterboxd rating, **When** the
   operator views its row, **Then** the rating is shown as a link to
   that movie's Letterboxd page.
2. **Given** a movie has no resolved Letterboxd rating (not yet enriched
   or no Letterboxd match found), **When** the operator views its row,
   **Then** the row shows that no rating is available rather than a
   broken or dead link.

---

### Edge Cases

- Which showtime's date/time/ticket link represents a movie once
  multiple showings are consolidated into one row? The movie's next
  upcoming active showing at that venue (the same "earliest active
  showtime" concept the app already uses for notifications) is shown, so
  the row always reflects an actionable, still-available showing.
- What happens if a movie's next showtime changes between page loads
  (e.g. the earliest one sells out or passes)? The listing always
  reflects current data at request time; no caching behavior changes
  are introduced by this feature.
- What happens to the "Recommended" highlighting and genre/poster
  columns that already exist per-row? They continue to apply to the
  single consolidated row per movie per venue; nothing about how a movie
  is marked recommended changes here.
- What happens for a movie whose only active showtime already has no
  ticket link or no Letterboxd match (the venue/site didn't provide
  one)? Handled today per-showtime already (missing link/rating shown as
  unavailable, per Edge Cases above) — consolidation doesn't change that
  handling, it only changes how many rows a movie occupies.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The listing page MUST show at most one row per distinct
  (movie, venue) combination, regardless of how many active showtimes
  that movie has at that venue.
- **FR-002**: When a movie has multiple active showtimes at a venue, the
  consolidated row MUST represent that movie's single earliest upcoming
  active showtime at that venue (consistent with how the app already
  determines "the" showtime to reference for a movie elsewhere, e.g. in
  notifications).
- **FR-003**: The listing page MUST display, for each consolidated row,
  a link to the ticket-purchase page for the showtime that row
  represents, when the source provided one for that showtime.
- **FR-004**: When no ticket-purchase link is available for the showtime
  a row represents, the listing page MUST show that as "unavailable"
  rather than an empty or broken link.
- **FR-005**: The listing page MUST display each movie's rating as a
  link to that movie's page on Letterboxd, when a Letterboxd match and
  rating have been resolved for that movie.
- **FR-006**: When no Letterboxd rating is available for a movie (not
  yet enriched, or no Letterboxd match found), the listing page MUST
  show that as "unavailable" rather than an empty or broken link.
- **FR-007**: Consolidation MUST NOT change which movies are marked
  "Recommended" or otherwise alter existing genre/poster display
  behavior — those continue to apply per movie per venue exactly as they
  do today, now attached to the single consolidated row.
- **FR-008**: The ingestion health page and underlying showtime data
  storage MUST remain unaffected by this feature — consolidation is a
  presentation-layer change to the listing page only, not a change to
  what showtime data is captured or retained.

### Key Entities

- **Listing row (presentation concept)**: Not a new stored entity — a
  view-layer grouping of existing `Showtime` records by (movie title,
  venue), represented on screen by that group's single earliest
  upcoming active showtime, its ticket link, and the movie's existing
  metadata/recommendation/rating data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For any venue with N active showtimes across M distinct
  movies, the listing page renders exactly M rows for that venue (never
  N), regardless of how many showtimes each movie has.
- **SC-002**: An operator can identify, for any movie shown on the
  listing page, a working purchase link whenever one was captured from
  the source, without leaving the listing page to search for it.
- **SC-003**: An operator can reach a movie's Letterboxd page directly
  from the listing page's rating display whenever a Letterboxd rating is
  available, without a separate search.
- **SC-004**: Movies with no available ticket link or no available
  Letterboxd rating are always shown with a clear "unavailable"
  indicator rather than a non-functional link, in 100% of such cases.

## Assumptions

- "One listing per movie per venue" refers to the primary showtimes
  listing page (`GET /`); the separate ingestion health page (`GET
  /health`) is out of scope and unaffected.
- The Letterboxd rating and Letterboxd URL both come from the app's
  existing Letterboxd match/rating data for a movie (already fetched for
  recommendation-decision purposes); this feature surfaces that existing
  data in the UI rather than fetching any new information from
  Letterboxd.
- "The rating" the operator wants linked to Letterboxd is the Letterboxd
  rating specifically (the source the operator already trusts for
  recommendation decisions per the app's existing recommendation logic),
  not the TMDB rating the page happens to also have on hand — since the
  request is explicitly to link it to Letterboxd.
- No new data needs to be captured from cinema sources or Letterboxd for
  this feature; all data involved (ticket links, Letterboxd ratings/
  slugs) is already ingested/enriched by existing features.
