# Internal Interface Contract: Onboarded Best-of List Set

This feature's only "interface" is internal — an extension of feature
003's `letterboxd_client.BUILT_IN_BEST_OF_LISTS` constant and the
`reasons` string it feeds into (see feature 003's
[recommendation-interface.md](../../003-showtime-recommendation-rules/contracts/recommendation-interface.md),
which this extends rather than replaces). No new HTTP-facing API or
route is introduced.

## `letterboxd_client.BUILT_IN_BEST_OF_LISTS: dict[str, BestOfList]`

**Contract**:
- Every entry's `url` MUST point to a Letterboxd list page using the
  same poster-grid + pagination markup `fetch_best_of_list_slugs`
  already parses (`data-target-link="/film/{slug}/"`, `.../page/{n}/`) —
  verified per entry before being added (Constitution Principle VII).
- Every entry's `display_name` MUST be a human-readable string suitable
  for direct display to the operator (web view and Discord
  notifications) with no further transformation.
- `official_top_250` (feature 003) plus the 8 lists in data-model.md are
  present; the dict MAY grow in future features but MUST NOT shrink
  without an explicit, separately-justified removal (an operator who
  already has recommendations keyed to a removed list_key would see
  that list's contribution to `reasons` silently disappear).

## `storage.get_movie_recommendation(db_path, movie_title) -> MovieRecommendation | None`

Unchanged signature and return-value contract from feature 003. The only
change observable to callers (feature 004's notifications, this
project's web view) is the *content* of `reasons` for best-of-list
matches: a human-readable list `display_name` instead of a raw
`best_of:{key}` token (data-model.md). Consumers that only display
`reasons` verbatim (both existing consumers) require no code change.
Any future consumer that pattern-matches `reasons` by the
`best_of:{key}` prefix would break — none currently exists (verified by
repo-wide search during planning), so this is not a breaking change in
practice, but is called out here as the one behavioral difference a
future maintainer should know about.

## Web View Extension (`GET /`)

No new route. The existing "Recommended (…)" reason text (feature 003's
web view contract) now names specific onboarded lists by their real
title instead of only ever showing `best_of:official_top_250` for
list-based matches.
