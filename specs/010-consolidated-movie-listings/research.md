# Research: Consolidated Movie Listings with Ticket and Letterboxd Links

## 1. How to pick "the" showtime a consolidated row represents

**Current behavior**: `web.py`'s `listing()` view calls
`storage.list_active_showtimes(db_path, cinema.id)` and renders one
`<tr>` per row returned — one per active `Showtime` record, ordered by
`show_date, start_time` (per `list_active_showtimes`'s own `ORDER BY`).

**Decision**: Group the showtimes already returned by `list_active_showtimes`
by `movie_title` in the view layer, and take the first showtime in each
group as the row's representative — since `list_active_showtimes` is
already ordered by `show_date, start_time`, the first showtime per movie
in iteration order is already that movie's earliest upcoming one. This
is the exact same "earliest active showtime" semantics
`storage.get_next_showtime_for_movie` already implements for feature
004's notifications, just derived from data already fetched for the page
rather than issuing one query per movie.

**Rationale**: `list_active_showtimes` already returns exactly the
active-showtime rows the page needs, in the right order, in one query
per cinema — grouping that single result set in Python needs no new
query at all. Calling `get_next_showtime_for_movie` once per distinct
movie title instead would add N extra queries per page load (N = number
of distinct movies at that cinema) for the same answer, since the
ordering guarantee already makes "first showtime seen per movie" and
"movie's earliest active showtime" identical results.

**Alternatives considered**:
- Call `storage.get_next_showtime_for_movie` per distinct movie title —
  rejected: functionally equivalent result, extra N queries per page
  load for no benefit, since `list_active_showtimes` already returns the
  same ordered data.
- Add a new `storage` function that does the grouping in SQL (e.g. `GROUP
  BY movie_title` with a min-date/time subquery) — rejected: unjustified
  complexity (Constitution IV) for what a single Python grouping pass
  over an already-fetched, already-ordered list accomplishes just as
  correctly; SQLite's per-request data volume here (one cinema's active
  showtimes) is far too small for a query-side optimization to matter.

## 2. Ticket link source

**Decision**: Use the representative showtime's existing `ticket_url`
field directly (`Showtime.ticket_url`, already populated by every
scraper per feature 001/004's "Decision: Ticket link (FR-002a) requires
no new data source" research finding, and already used by `notify.py`'s
message templates). No new data capture needed — this feature only adds
it to the listing page template.

**Rationale**: The field already exists on every `Showtime` row and is
already treated elsewhere in the app (feature 004) as "may be `None`,
render as absent rather than a broken link" — the exact handling FR-004
asks for here. Reusing the same field/convention keeps the ticket-link
display consistent with how the notification messages already present
it.

**Alternatives considered**: None — this is a direct, unambiguous reuse
of existing data; no alternative sourcing makes sense.

## 3. Letterboxd rating + link source

**Decision**: Use `storage.get_letterboxd_movie_data(db_path, movie_title)`
(already populated by `recommend.py`'s `_ensure_letterboxd_data_cached`,
per feature 003) to get both the rating (`LetterboxdMovieData.average_rating`)
and the slug needed to build the link
(`f"https://letterboxd.com/film/{letterboxd_slug}/"`, matching the exact
URL template `letterboxd_client.fetch_movie_rating` already uses
internally). Both are required to show a working, meaningful link: if
`letterboxd_slug` is `None` (no Letterboxd match found) or
`average_rating` is `None` (matched, but the rating fetch itself failed
or hasn't completed), the row shows "unavailable" rather than a link
with no number, or a rating number with nowhere to click.

**Rationale**: This is the app's existing Letterboxd data path (feature
003), already fetched independently of TMDB metadata — using it directly
avoids fetching anything new and matches the spec's explicit ask ("link
to Letterboxd," not TMDB). The existing `MovieMetadata.average_rating`
field (TMDB's own rating, already shown in today's UI) is left in place
for the genre/poster columns' existing "matched" branch, but is no
longer what's rendered under the "Rating" column — replaced by the
Letterboxd figure per spec Assumptions.

**Alternatives considered**:
- Link the existing TMDB `average_rating` to a TMDB page instead —
  rejected: contradicts the explicit request ("link to Letterboxd").
- Show both TMDB and Letterboxd ratings side by side — rejected as scope
  creep beyond what was asked; the spec's Assumptions section already
  resolves "which rating" in favor of Letterboxd alone, and Constitution
  IV favors the simpler single-rating change actually requested.

## 4. Grouping scope: per cinema section, not across cinemas

**Decision**: Perform the per-movie grouping independently within each
`cinema_sections` entry `web.py` already builds (one `Showtime` list per
cinema) — never merging rows across venues. A movie playing at two
venues still produces two rows total (one under each venue's existing
`<h1>{{ section.cinema.name }} Showtimes</h1>` section), per spec User
Story 1 Acceptance Scenario 2.

**Rationale**: The existing template already partitions showtimes into
one section per cinema before rendering rows; grouping by movie title
within that existing per-cinema list preserves that partition for free
— no restructuring of the section-building loop is needed, only how
each section's own showtime list is transformed into rows.

**Alternatives considered**: None — cross-venue merging was never in
scope (spec explicitly says "one listing per movie for each venue").
