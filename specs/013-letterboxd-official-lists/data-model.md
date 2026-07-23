# Data Model: Letterboxd Official Lists as Recommendation Filters

No schema changes. This feature reuses feature 003's existing
`letterboxd_reference_list` table and `movie_recommendation.reasons`
column unchanged — see
[003's data-model.md](../003-showtime-recommendation-rules/data-model.md)
for their full field definitions. Only the *set* of `list_key` values fed
into that existing schema grows, and the *content* written into
`reasons` for best-of-list matches changes from a raw key to a display
name (see research.md).

## Onboarded Official List (in-code, not a DB table)

Extends `BUILT_IN_BEST_OF_LISTS` (`letterboxd_client.py`) from
`dict[str, str]` (`list_key → URL`) to `dict[str, BestOfList]`, where
`BestOfList` is a small structure of:

| Field | Type | Notes |
|---|---|---|
| `display_name` | text | Human-readable list name shown in recommendation reasons, e.g. `"Top 250 Horror Films"` |
| `url` | text | The list's Letterboxd page, e.g. `https://letterboxd.com/official/list/top-250-horror-films/` |

The dict key itself remains the stable internal `list_key` used as the
`letterboxd_reference_list.list_key` cache partition (`f"best_of:{key}"`)
and is never shown to the operator — only `display_name` is.

**The 8 new entries** (research.md live-verified URLs, all under
Letterboxd's own `letterboxd.com/official/` account):

| `list_key` | `display_name` |
|---|---|
| `top_500` | Letterboxd's Top 500 Films |
| `most_fans` | Top 250 Films with the Most Fans |
| `top_250_animated` | Top 250 Animated Films |
| `top_250_horror` | Top 250 Horror Films |
| `top_250_documentary` | Top 250 Documentary Films |
| `top_250_women_directors` | Top 250 Films by Women Directors |
| `top_250_black_directors` | Top 250 Films by Black Directors |
| `top_100_underseen` | Top 100 Underseen Films |

(`official_top_250`, the existing feature-003 entry, is unchanged.)

## Movie Recommendation `reasons` (existing column, changed content)

`movie_recommendation.reasons` (feature 003's data-model.md) remains a
flat, comma-joined text column. The only change: a best-of-list match
now contributes that list's `display_name` (e.g. `"Top 250 Horror
Films"`) instead of `f"best_of:{list_key}"` (e.g. `"best_of:top_250_horror"`).
`"watchlist"` and `"rating"` tokens are unchanged.

Example: a movie on both the watchlist and two onboarded lists now
produces `reasons = "watchlist,Top 250 Horror Films,Top 250 Animated Films"`
instead of `"watchlist,best_of:top_250_horror,best_of:top_250_animated"`.
