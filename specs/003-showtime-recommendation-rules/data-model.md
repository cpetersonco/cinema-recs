# Data Model: Showtime Recommendation Rules

These tables extend the existing SQLite schema (same `cinema_recs.db`
file used by features 001/002). Like feature 002's `movie_metadata`,
movie identity here is the `movie_title` string (the join key back to
`showtime.movie_title` and to `movie_metadata.movie_title`) — no separate
movie entity exists in this project's schema.

## Letterboxd Movie Data

Per-movie data resolved from feature 002's TMDB identifier (spec FR-012)
and cached (research.md: "cache per-movie data, always re-fetch list
membership").

| Field | Type | Notes |
|---|---|---|
| `id` | integer, primary key | |
| `movie_title` | text, not null, unique | Join key to `showtime.movie_title` / `movie_metadata.movie_title` |
| `tmdb_id` | integer, not null | Copied from `movie_metadata.tmdb_id` at fetch time, for traceability |
| `letterboxd_slug` | text, nullable | Set when `letterboxd.com/tmdb/{tmdb_id}/` resolves; `NULL` means no Letterboxd page found (FR-004) |
| `average_rating` | real, nullable | Letterboxd's 0.5-5 scale (distinct from feature 002's TMDB 0-10 `average_rating`) |
| `fetched_at` | timestamp, not null | |

**Uniqueness rule**: `movie_title` is unique — one row per distinct
matched movie, populated only for movies with a `movie_metadata` row
where `match_status = "matched"` (per FR-004/FR-012, unmatched movies are
never looked up on Letterboxd at all).

## Letterboxd Reference List (cache)

Caches the *membership* of a Letterboxd list (the operator's watchlist,
or a built-in best-of list) as a set of film slugs, refreshed each
evaluation cycle (FR-002/FR-007). Per the spec's resilience edge case, a
failed refresh leaves the existing rows for that `list_key` untouched.

| Field | Type | Notes |
|---|---|---|
| `id` | integer, primary key | |
| `list_key` | text, not null | `"watchlist"` or `"best_of:{key}"` (e.g. `"best_of:official_top_250"`) |
| `film_slug` | text, not null | e.g. `"the-godfather"` |
| `fetched_at` | timestamp, not null | Timestamp of the fetch that populated this row |

**Refresh rule**: On a *successful* fetch of `list_key`, all existing
rows for that `list_key` are deleted and replaced with the freshly
scraped set in one operation. On a *failed* fetch, no rows for that
`list_key` are touched (stale-but-present data is preferred over treating
the list as empty, per the spec's edge case).

**Uniqueness rule**: `(list_key, film_slug)` unique — a slug appears at
most once per list.

## Movie Recommendation

The derived recommendation result for a movie (spec FR-003, FR-011),
recomputed every evaluation cycle from the current `Letterboxd Movie
Data`, `Letterboxd Reference List` cache, and `Recommendation
Configuration` (env vars, not a DB table — see below).

| Field | Type | Notes |
|---|---|---|
| `id` | integer, primary key | |
| `movie_title` | text, not null, unique | Join key, same convention as above |
| `is_recommended` | integer (0/1), not null | |
| `reasons` | text, nullable | Comma-delimited subset of `watchlist`, `rating`, `best_of:{key}`; `NULL` when `is_recommended = 0` |
| `evaluated_at` | timestamp, not null | |

**Uniqueness rule**: `movie_title` is unique — one current recommendation
result per movie, overwritten (not appended) on each evaluation, since
only the *current* status matters (spec's Key Entities: "Recomputed
whenever either input changes").

## Recommendation Configuration

Per the spec's Assumptions, this is **not** a database table — it is
process configuration, following the same env-var pattern as features
001/002 (see research.md: "Config takes effect via container restart"):

| Env var | Purpose | Required |
|---|---|---|
| `LETTERBOXD_USERNAME` | Source for the watchlist criterion (FR-001, FR-009) | No |
| `LETTERBOXD_RATING_THRESHOLD` | Minimum Letterboxd rating (0.5-5) for the rating criterion (FR-001) | No — invalid/non-numeric values are treated as unset (FR-008), not a startup error |

## Relationships

```
Movie Metadata.movie_title (feature 002, match_status="matched")
  ──< (referenced by, not FK) Letterboxd Movie Data.movie_title
Letterboxd Movie Data.letterboxd_slug
  ──< (looked up against) Letterboxd Reference List.film_slug
Letterboxd Movie Data.movie_title, Letterboxd Reference List (all list_keys), Recommendation Configuration
  ──> (computed into) Movie Recommendation.movie_title
```

No foreign key constraints are added, consistent with feature 002's
title-string-keyed join pattern (this project's schema has no separate
movie entity to key against).

## Cross-feature note (feature 004)

Feature 004 (showtime notifications) reads `movie_recommendation` (by
`movie_title`, joined via `showtime.movie_title`) to decide which
showtimes to notify about, and `reasons` to describe why (per FR-011).
It does not need `Letterboxd Movie Data` or `Letterboxd Reference List`
directly — those are this feature's internal working data.
