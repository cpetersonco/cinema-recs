# Phase 0 Research: Letterboxd Official Lists as Recommendation Filters

## Decision: The 8 onboarded lists live under Letterboxd's own `/official/` curator account, and share the existing scraper's markup

**Rationale**: All 8 lists selected for FR-001 were confirmed live during
planning (per Constitution Principle VII) by fetching each list page and
verifying it exposes `data-target-link="/film/{slug}/"` poster-grid
entries and `.../page/{n}/` pagination links — the exact two markers
`letterboxd_client._fetch_paginated_slugs` already parses for the
existing Top 250 list (via `_TARGET_LINK_SLUG_RE` / `_PAGE_NUMBER_RE`).
No new parsing logic is needed; `fetch_best_of_list_slugs` (already
public in `letterboxd_client.py`) works unmodified against each new URL.

Live-checked URLs and results (`GET`, same-origin fetch from an
authenticated browser session on 2026-07-23):

| List | URL | Status | Films on page 1 | Pages |
|------|-----|--------|-----------------:|------:|
| Letterboxd's Top 500 Films | `/official/list/letterboxds-top-500-films/` | 200 | 100 | 5 |
| Top 250 Films with the Most Fans | `/official/list/top-250-films-with-the-most-fans/` | 200 | 100 | 3 |
| Top 250 Animated Films | `/official/list/top-250-animated-films/` | 200 | 100 | 3 |
| Top 250 Horror Films | `/official/list/top-250-horror-films/` | 200 | 100 | 3 |
| Top 250 Documentary Films | `/official/list/top-250-documentary-films/` | 200 | 100 | 3 |
| Top 250 Films by Women Directors | `/official/list/top-250-films-by-women-directors/` | 200 | 100 | 3 |
| Top 250 Films by Black Directors | `/official/list/top-250-films-by-black-directors/` | 200 | 100 | 3 |
| Top 100 Underseen Films | `/official/list/top-100-underseen-films/` | 200 | 100 | 1 |

Unlike the existing Top 250 list (a community clone hosted under a
regular user's account, per feature 003's research), these 8 lists are
hosted directly under Letterboxd's own `letterboxd.com/official/`
curator account — an operational improvement, since they're maintained
by Letterboxd staff/curators rather than depending on one community
member's account staying active.

**Alternatives considered**:
- Onboarding all 230+ lists tagged `official`: rejected per operator
  decision during `/speckit-specify` — would multiply this feature's
  scrape volume against Letterboxd by ~30x every refresh cycle for
  marginal recommendation value (most of the 230+ lists are niche
  year-in-review or tag-based lists unlikely to intersect with
  first-run theatrical showtimes), and is a much larger implementation
  than "a curated handful."
- A new parsing path (e.g. handling `Top 250 Short Films`, which is
  outside the movie-only scope per feature 002): rejected, consistent
  with this feature's Assumptions — TV/short-film lists aren't relevant
  to a cinema showtime app and needn't be onboarded at all.

## Decision: Reasons continue to be a flat, comma-joined string; list matches contribute a human-readable display name instead of a raw internal key

**Rationale**: `recommend.py` already builds `reasons` as a flat list of
tokens (`"watchlist"`, `"rating"`, `f"best_of:{list_key}"`) joined with
commas and stored/rendered as free text (`web.py`'s listing template and
`notify.py`'s Discord message both print `reasons` verbatim, per
grep — no code anywhere parses or pattern-matches individual tokens out
of that string). FR-004 requires the *specific list name* to be visible,
not an internal key like `best_of:top_250_horror`. The simplest change
consistent with that existing "flat string" contract (Simplicity
principle) is to change what `recommend.py` appends when a best-of list
matches: from `f"best_of:{list_key}"` to that list's human display name
(e.g. `"Top 250 Horror Films"`). `watchlist`/`rating` tokens are
unchanged — out of scope for this feature.

This requires each entry in the built-in best-of list set to carry both
a stable internal cache key (unchanged use: `f"best_of:{list_key}"` as
the `reference_list_slugs` cache partition key) and a human-readable
display name — today `BUILT_IN_BEST_OF_LISTS` is `dict[str, str]`
(key → URL); it becomes `dict[str, BestOfList]` where `BestOfList` is a
small dataclass/named tuple of `(display_name, url)`.

**Alternatives considered**:
- A separate `list_key → display_name` lookup performed at render time
  in `web.py`/`notify.py`: rejected — would duplicate the same mapping
  in two consumers and require parsing the `reasons` string back apart
  by prefix, more complex than storing the final display text once at
  the point reasons are built.
- Keeping raw keys and improving only the web view's presentation
  (e.g. a title-cased/underscore-replaced transform of the key):
  rejected — still wrong for `notify.py`'s Discord messages (FR-004
  doesn't exempt notifications), and title-casing a slug like
  `top_250_films_by_black_directors` produces an uglier, less accurate
  label than the list's actual Letterboxd title.

## Decision: No scheduler/config changes needed

**Rationale**: `_refresh_reference_lists` already iterates
`BUILT_IN_BEST_OF_LISTS.items()` in a loop with per-list
try/except (each list's fetch failure is isolated and logged, previous
cache kept) — this is exactly User Story 2 / FR-003's required
behavior today, for any number of dict entries. Adding 7 more entries
requires no change to `scheduler.py`, `config.py`, or the refresh-cycle
cadence (`config.refresh_interval_hours`); the loop and its isolation
guarantee already scale to N lists.
