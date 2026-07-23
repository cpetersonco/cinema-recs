# Internal Interface Contract: Movie Recommendation Lookup

This feature's primary "interface" is internal (a Python module boundary
consumed by feature 004), plus an extension to the existing web listing
view. There is no new HTTP-facing API.

## `storage.get_movie_recommendation(db_path, movie_title) -> MovieRecommendation | None`

Used by feature 004 (and this feature's own web view) to fetch a movie's
current recommendation status by its ingested title.

**Contract**:
- Returns `None` if recommendation evaluation has never run for that
  title (e.g. it hasn't been enriched/matched yet, or evaluation hasn't
  run since it was ingested).
- Returns a `MovieRecommendation` row with `is_recommended = False` and
  `reasons = None` if evaluation ran but no criterion matched — including
  the case where the movie has no resolvable Letterboxd entry (FR-004) or
  no configuration is active at all (FR-005).
- Returns a `MovieRecommendation` row with `is_recommended = True` and a
  non-empty, comma-delimited `reasons` string (one or more of
  `watchlist`, `rating`, `best_of:{key}`) otherwise (FR-011).

**Consumer guarantee**: Feature 004 MUST treat any row where
`is_recommended != True` (including no row at all) as "do not notify
about this showtime" — it must not notify based on partial/absent
recommendation data.

## Web View Extension (`GET /`)

Extends feature 001/002's existing listing view contract.

**Addition**: For each showtime row where `is_recommended = True`, the
listing visually distinguishes it (badge/highlight) and surfaces the
matched `reasons` (FR-006, FR-011, User Story 2 acceptance scenario 1).
For showtimes whose movie is not recommended (including "not yet
evaluated"), the row displays exactly as it does today, with no broken or
missing section (User Story 2 acceptance scenario 2).

No new routes are introduced by this feature.
