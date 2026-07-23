# Internal Interface Contract: Movie Metadata Lookup

This feature's primary "interface" is internal (a Python module boundary
consumed by feature 003), plus an extension to feature 001's existing
web view. There is no new HTTP-facing API.

## `storage.get_movie_metadata(db_path, movie_title) -> MovieMetadata | None`

Used by feature 003 (and this feature's own web view) to fetch a movie's
enrichment record by its ingested title.

**Contract**:
- Returns `None` if no enrichment attempt has been made yet for that
  title.
- Returns a `MovieMetadata` row with `match_status = "unmatched"` and
  `tmdb_id = None` if TMDB enrichment ran but found no confident match.
- Returns a `MovieMetadata` row with `match_status = "matched"` and a
  non-null `tmdb_id` otherwise — this is the field feature 003 uses to
  resolve the corresponding Letterboxd entry (spec FR-009).

**Consumer guarantee**: Feature 003 MUST treat any row where
`match_status != "matched"` (including no row at all) as "cannot resolve
Letterboxd data for this movie" — it must not attempt Letterboxd
resolution without a `tmdb_id`.

## Web View Extension (`GET /`)

Extends feature 001's existing listing view contract
(`specs/001-cinepolis-showtime-ingestion/contracts/web-view.md`).

**Addition**: For each showtime row where a matched `MovieMetadata`
record exists, the listing additionally displays genre(s), average
rating, and poster. For showtimes whose movie is unmatched (or not yet
attempted), the row displays exactly as it does today (per feature 001),
with no broken or missing section (spec FR-007, User Story 3 acceptance
scenario 2).

No new routes are introduced by this feature.
