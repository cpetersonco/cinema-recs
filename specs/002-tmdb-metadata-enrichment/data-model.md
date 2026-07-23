# Data Model: Movie Metadata Enrichment via TMDB

These tables extend feature 001's existing SQLite schema (same database
file, same `cinema.db` path). Movie identity in this project is
currently just the `movie_title` string on `showtime` rows (feature 001
has no separate `movie` entity), so `movie_metadata` is keyed on the
normalized title rather than a foreign key.

## Movie Metadata

Represents TMDB-sourced information for a distinct movie title (spec
FR-002, FR-004).

| Field | Type | Notes |
|---|---|---|
| `id` | integer, primary key | |
| `movie_title` | text, not null, unique | The title as ingested by feature 001 (the join key back to `showtime.movie_title`) |
| `match_status` | text, not null | `matched` or `unmatched` |
| `tmdb_id` | integer, nullable | Set only when `match_status = matched`. This is the value feature 003 uses as the "translation surface" to Letterboxd (spec FR-009) |
| `tmdb_title` | text, nullable | Title as returned by TMDB (may differ slightly from the ingested title) |
| `genres` | text, nullable | Stored as a simple delimited list (e.g. comma-separated) — no separate genre table needed at this scale |
| `overview` | text, nullable | |
| `release_year` | integer, nullable | |
| `average_rating` | real, nullable | TMDB's 0-10 rating scale (distinct from feature 003's Letterboxd 0.5-5 rating, which is fetched separately by that feature) |
| `runtime_minutes` | integer, nullable | |
| `poster_path` | text, nullable | TMDB poster reference (path or URL, per whatever `enrich.py` stores) |
| `last_enriched_at` | timestamp, not null | |

**Uniqueness rule**: `movie_title` is unique — one metadata row per
distinct ingested title, matching FR-003's caching requirement.

## Enrichment Attempt

Represents one attempt to enrich a specific movie title (spec FR-008),
mirroring feature 001's `ingestion_run` observability entity.

| Field | Type | Notes |
|---|---|---|
| `id` | integer, primary key | |
| `movie_title` | text, not null | |
| `attempted_at` | timestamp, not null | |
| `outcome` | text, not null | `matched`, `unmatched`, or `failed` |
| `error_message` | text, nullable | Populated when `outcome = failed` (e.g., TMDB unreachable) |

## Relationships

```
Showtime.movie_title (feature 001) ──< (referenced by, not FK) Movie Metadata.movie_title
Movie Metadata.movie_title ──< (many) Enrichment Attempt.movie_title
```

No foreign key constraint is added from `showtime` to `movie_metadata`
since feature 001's schema doesn't have a separate movie entity to key
against — the join is by matching title strings, consistent with how
feature 001 itself identifies movies today.

## Cross-feature note (feature 003)

Feature 003 reads `movie_metadata.tmdb_id` (only for rows where
`match_status = matched`) to resolve each movie's Letterboxd entry. It
does not read `genres`, `average_rating` (TMDB scale), or any other
display-only field — those exist solely for this feature's own listing
view enhancement (User Story 3).
