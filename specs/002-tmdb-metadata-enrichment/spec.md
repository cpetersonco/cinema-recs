# Feature Specification: Movie Metadata Enrichment via TMDB

**Feature Branch**: `002-tmdb-metadata-enrichment`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "movie metadata enrichment via TMDB"

## Clarifications

### Session 2026-07-22

- Q: Should feature 003 (recommendation rules) use this feature's TMDB match to locate a movie's corresponding Letterboxd entry, rather than matching the raw scraped title against Letterboxd independently? → A: Yes. This feature's TMDB match is a reliable "translation surface" between the messy scraped cinema title and Letterboxd's catalog, since Letterboxd's own catalog exposes films by TMDB identifier. This re-establishes feature 003 as a downstream consumer of this feature's matching work, in addition to this feature's original display-metadata purpose.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enrich ingested movies with metadata (Priority: P1)

As the operator, I want each distinct movie title captured by showtime
ingestion to be enriched with metadata (genre, overview, release year,
rating, runtime, poster) from The Movie Database (TMDB), so the showtime
listing shows more than a bare title and can eventually support
recommendation logic.

**Why this priority**: Enrichment is the foundation everything else in
this feature (and future recommendation features) depends on — without
it there is no metadata to display, filter, or recommend on.

**Independent Test**: Can be fully tested by ingesting a showtime for a
known movie title and confirming a metadata record (genre, overview,
release year, rating, runtime, poster reference) is fetched and stored
for that movie.

**Acceptance Scenarios**:

1. **Given** a newly ingested showtime for a movie with no existing
   metadata record, **When** enrichment runs, **Then** the system queries
   TMDB and stores a metadata record linked to that movie title.
2. **Given** a movie that already has a stored metadata record, **When**
   another showtime for the same movie is ingested, **Then** the system
   reuses the existing record instead of querying TMDB again.

---

### User Story 2 - Handle movies TMDB can't confidently match (Priority: P2)

As the operator, I want movies that can't be confidently matched to a TMDB
entry to be clearly marked as unmatched rather than silently attached to
the wrong movie's metadata, so incorrect enrichment doesn't erode trust in
the listing.

**Why this priority**: Wrong metadata (attaching one movie's poster/rating
to a different movie) is worse than no metadata — it actively misleads
rather than just being incomplete.

**Independent Test**: Can be fully tested by ingesting a showtime for a
title that doesn't exist in TMDB (or is too ambiguous to match
confidently) and confirming the system records it as unmatched rather
than attaching any metadata.

**Acceptance Scenarios**:

1. **Given** a movie title with no corresponding TMDB result, **When**
   enrichment runs, **Then** the system records the movie as unmatched and
   the listing shows it without fabricated metadata.
2. **Given** a movie title with multiple ambiguous TMDB candidates and no
   confident way to pick one, **When** enrichment runs, **Then** the
   system records it as unmatched rather than guessing.

---

### User Story 3 - View enriched showtimes (Priority: P2)

As the operator, I want the existing showtime listing view to display
enriched metadata (genre, rating, poster) alongside each showtime when
available, so the listing is immediately more useful without needing to
look anything up separately.

**Why this priority**: Enrichment only delivers value once it's visible;
this is the smallest change that surfaces it.

**Independent Test**: Can be fully tested by ingesting and enriching a
known movie, then confirming the listing view shows its genre, rating,
and poster alongside the existing showtime fields.

**Acceptance Scenarios**:

1. **Given** a showtime for a movie with stored metadata, **When** the
   operator views the listing, **Then** genre, rating, and poster are
   displayed alongside the existing showtime fields (movie title, date,
   start time, format).
2. **Given** a showtime for a movie marked unmatched, **When** the
   operator views the listing, **Then** the showtime still displays
   normally with its existing fields, without a broken or missing
   metadata section.

---

### Edge Cases

- What happens when TMDB is temporarily unreachable during enrichment?
  The showtime itself must still be ingested and shown; enrichment should
  be retried on a later run rather than blocking ingestion.
- How does the system handle a movie title that changes slightly between
  ingestion runs (e.g., punctuation or subtitle differences) — does it
  create a second metadata lookup for what is really the same movie?
- What happens when TMDB rate limits are hit during a run with many new
  movies at once?
- What happens when a movie is a re-release or has the same title as an
  older, unrelated film (ambiguous match)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST query TMDB for metadata for every distinct
  movie title observed in ingested showtimes that does not already have a
  stored metadata record (matched or unmatched).
- **FR-002**: For each successfully matched movie, the system MUST store:
  TMDB identifier, title (as returned by TMDB), genre(s), overview,
  release year, average rating, runtime, and a poster image reference.
- **FR-003**: The system MUST cache metadata per distinct movie title so
  repeated showtimes for the same movie do not trigger repeated TMDB
  lookups.
- **FR-004**: The system MUST mark a movie as unmatched, without
  attaching any metadata, when TMDB returns no result or when no
  candidate result is a clearly best match (see Assumptions for the
  matching rule).
- **FR-005**: The system MUST NOT block or fail showtime ingestion when
  TMDB is unreachable or a lookup fails; the affected movie(s) remain
  unmatched until a later enrichment attempt succeeds.
- **FR-006**: The system MUST respect TMDB's API rate limits, spacing out
  or retrying requests rather than firing them all at once when many new
  movies appear in a single ingestion run.
- **FR-007**: The showtime listing view MUST display genre, rating, and
  poster for movies with stored metadata, and MUST continue displaying
  showtimes normally (without a broken or missing section) for unmatched
  movies.
- **FR-008**: The system MUST record, for each enrichment attempt,
  whether it succeeded (matched), was recorded unmatched, or failed
  (e.g., TMDB unreachable) — mirroring the existing ingestion-run
  observability pattern — so enrichment health can be checked the same
  way ingestion health is.
- **FR-009**: The stored TMDB identifier for each matched movie MUST be
  usable by other features (specifically feature 003) as a reliable key
  for locating that movie's corresponding entry in other film catalogs
  (e.g., Letterboxd), not just for TMDB's own display metadata. This
  feature does not perform that cross-catalog lookup itself — it only
  guarantees the TMDB identifier it stores is accurate enough to be used
  for it.

### Key Entities

- **Movie Metadata**: Represents TMDB-sourced information for a distinct
  movie title. Attributes: movie title (as ingested), match status
  (matched/unmatched), TMDB identifier (if matched), genre(s), overview,
  release year, average rating, runtime, poster reference, last enriched
  timestamp.
- **Enrichment Attempt**: Represents one attempt to enrich a specific
  movie title. Attributes: movie title, attempted-at timestamp, outcome
  (matched/unmatched/failed), error message (if failed). Mirrors the
  existing Ingestion Run entity's observability role, scoped to
  enrichment instead of showtime fetching.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 90% of distinct movie titles ingested for the
  alpha cinema are successfully matched to TMDB metadata (the remainder
  legitimately unmatched, e.g. very new or region-specific titles).
- **SC-002**: A given movie's metadata is fetched from TMDB at most once;
  every subsequent showtime referencing the same movie reuses the cached
  record.
- **SC-003**: Showtime ingestion completes normally (not blocked or
  delayed) even when TMDB is completely unreachable during a run.
- **SC-004**: The operator can view genre, rating, and poster for any
  matched movie directly in the existing listing view without visiting
  any external site.
- **SC-005**: No movie is ever displayed with another movie's metadata
  (zero mismatched-metadata incidents).

## Assumptions

- TMDB (The Movie Database) is used as the metadata source; an API key
  will be supplied via configuration, consistent with how other
  feature 001 settings are provided as environment variables.
- Enrichment runs as part of or immediately following the existing
  ingestion cycle (per feature 001), operating on movie titles already
  captured — this feature does not introduce a new independent trigger
  schedule.
- Matching is based on title (and release year when available) with a
  popularity/similarity tiebreaker; when no single candidate clearly
  stands out as the best match, the movie is recorded unmatched rather
  than guessing. No manual/human-in-the-loop matching review is in scope
  for this phase.
- Only the single alpha cinema's ingested movies are in scope, consistent
  with feature 001's current scope.
- Filtering, sorting, or searching the listing by metadata (e.g., "show
  only 4-star-and-up movies") is explicitly out of scope for this
  feature — this feature only enriches and displays metadata inline;
  filtering/sorting is left for a future feature.
- **Feature 003 (Showtime Recommendation Rules) depends on this
  feature**: it uses this feature's TMDB match/identifier to locate each
  movie's Letterboxd entry, rather than matching the raw scraped title
  against Letterboxd independently. A movie unmatched here (no TMDB
  result) is therefore also unresolvable in feature 003's Letterboxd-based
  criteria, even though feature 003 no longer uses this feature's
  genre/rating data directly.
