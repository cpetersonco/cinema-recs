# Data Model: Consolidated Movie Listings with Ticket and Letterboxd Links

No new persisted entities and no schema changes. This is a presentation-
layer feature (spec FR-008): it changes how `web.py` groups and renders
already-stored data, not what's captured or stored.

## Existing entities used (unchanged)

| Entity | Used for | Source |
|---|---|---|
| `Showtime` (`storage.list_active_showtimes`) | The set of active showtimes per cinema; grouped by `movie_title` in the view to pick each movie's earliest one (research.md §1) and its `ticket_url` (research.md §2) | Existing, feature 001/009 |
| `MovieMetadata` (`storage.get_movie_metadata`) | Genre and poster columns — unchanged from today | Existing, feature 002 |
| `MovieRecommendation` (`storage.get_movie_recommendation`) | "Recommended" row highlighting — unchanged from today | Existing, feature 003 |
| `LetterboxdMovieData` (`storage.get_letterboxd_movie_data`) | Rating value and Letterboxd film-page link (research.md §3); **newly read by `web.py`**, though the table/data itself already exists | Existing, feature 003 |

## New internal (non-persisted) concept: consolidated listing row

Not a database entity — a per-request, view-layer grouping built inside
`web.py`'s `listing()` handler: for each cinema section, group that
cinema's already-fetched active showtimes by `movie_title` and keep only
the first (earliest, per existing `ORDER BY show_date, start_time`)
showtime per group. The resulting one-row-per-movie list replaces the
per-showtime list currently passed into `LISTING_TEMPLATE`.

## Template rendering changes

| Column | Today | After this feature |
|---|---|---|
| Movie / Date / Start Time / Format | One row per showtime | One row per movie per venue, showing that movie's earliest active showtime's date/time/format |
| Rating | `MovieMetadata.average_rating` (TMDB), plain text | `LetterboxdMovieData.average_rating`, rendered as a link to `https://letterboxd.com/film/{letterboxd_slug}/` when both are present; "—" (unavailable) otherwise |
| *(new)* Ticket link | Not shown | Representative showtime's `ticket_url`, rendered as a link when present; "—" (unavailable) otherwise |
| Genre / Poster / Recommended | Per showtime row (effectively per movie already, since these don't vary by showing) | Unchanged — now attached to the single consolidated row instead of repeated per showtime row |

No state transitions are introduced; this feature does not change any
entity's lifecycle.
