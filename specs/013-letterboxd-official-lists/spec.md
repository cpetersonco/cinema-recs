# Feature Specification: Letterboxd Official Lists as Recommendation Filters

**Feature Branch**: `013-letterboxd-official-lists`

**Created**: 2026-07-23

**Status**: Draft

**Input**: User description: "onboard the rest of these letterboxd official lists as recommendation filters for movies. https://letterboxd.com/official/lists/by/popular/"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See why a showtime matched a curated list (Priority: P1)

As the operator, when a showtime's movie appears on one of Letterboxd's
official curated lists (e.g. "Top 250 Horror Films", "Top 250 Animated
Films"), I want the recommendation to be marked and the specific list
named as the reason, so I know why the app is calling it out beyond just
"it's on some best-of list somewhere."

**Why this priority**: This is the core value of the feature — today
(feature 003) only one built-in list ("Official Top 250 Narrative Feature
Films") drives recommendations. Every other official list is currently
invisible to the recommendation engine no matter how well a movie ranks
on it.

**Independent Test**: Configure one additional built-in list, seed a
showtime whose movie is on that list but not on the existing Top 250 list
or the watchlist, run recommendation evaluation, and confirm the showtime
is marked recommended with that list named in the reasons.

**Acceptance Scenarios**:

1. **Given** a movie that appears on a newly onboarded official list but
   matches no other recommendation criterion, **When** recommendation
   evaluation runs, **Then** the movie's showtimes are marked recommended
   and the reasons include that specific list's name.
2. **Given** a movie that appears on more than one onboarded official
   list, **When** recommendation evaluation runs, **Then** the reasons
   include every matching list, not just the first one found.
3. **Given** a movie that appears on none of the onboarded official
   lists and matches no other criterion, **When** recommendation
   evaluation runs, **Then** it is not marked recommended on the basis of
   any list.

---

### User Story 2 - Lists stay current without a redeploy (Priority: P2)

As the operator, I want each onboarded list's membership to refresh on
the same cadence as the existing Top 250 list, so that a list Letterboxd
updates periodically (e.g. annual "Top 250 Animated Films" refresh) keeps
recommending correctly without me touching the app.

**Why this priority**: Consistent with FR-007 of feature 003; a list
that silently goes stale would quietly stop being useful and nobody would
notice.

**Independent Test**: Refresh reference lists, confirm each onboarded
list's cached film set is populated from the live Letterboxd page, and
confirm a fetch failure for one list doesn't wipe that list's previously
cached membership or block the others from refreshing.

**Acceptance Scenarios**:

1. **Given** the reference-list refresh cycle runs, **When** it
   completes, **Then** every onboarded list's cached membership reflects
   the current contents of its Letterboxd page.
2. **Given** one onboarded list's page is temporarily unreachable,
   **When** the refresh cycle runs, **Then** that list's previously
   cached membership is kept as-is and the other lists still refresh
   normally.

---

### User Story 3 - Distinguish lists from each other in the UI (Priority: P3)

As the operator viewing the showtime list, I want to see which specific
official list(s) each recommended movie matched, not a generic "on a
best-of list" label, so the recommendation reason is actually
informative.

**Why this priority**: Nice-to-have polish once multiple lists exist;
without it, User Story 1's per-list detail is captured internally but not
visible where the operator actually looks (the showtime web view).

**Independent Test**: View the web listing for a showtime recommended via
two different onboarded lists and confirm both list names appear in the
displayed reason text.

**Acceptance Scenarios**:

1. **Given** a recommended showtime matched via one or more onboarded
   lists, **When** the operator views the showtime listing, **Then** the
   displayed reason names each matching list.

---

### Edge Cases

- What happens when an onboarded list is deleted or renamed on
  Letterboxd (its page starts 404ing)? The list's previously cached
  membership should be kept (same "stale cache over false negative"
  behavior as an existing list going temporarily unreachable), and this
  should be visible in logs so the operator notices during periodic
  maintenance.
- What happens when the same movie appears on both the existing Top 250
  list and a newly onboarded list? Both should be recorded as separate
  matched reasons (per existing FR-011 behavior of recording all matched
  criteria).
- What happens when an official list contains non-movie entries (TV
  seasons, miniseries) that fall outside this app's movie-only scope?
  Those entries are simply never matched against any showtime, since
  showtimes are always movies (feature 002) — no special handling needed.
- What happens when Letterboxd changes an onboarded list's page markup in
  a way the existing scraper's poster-grid parser can't handle? Treated
  like any other scrape failure for that list (see User Story 2) —
  previously cached membership is kept, not wiped.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST check movies against an expanded fixed,
  built-in set of Letterboxd's official curated lists, extending the set
  established by feature 003's FR-010 beyond just "Official Top 250
  Narrative Feature Films" to include the following additional lists
  (a curated handful of the most popular official lists, not the full
  230+ lists Letterboxd's official-lists page hosts):
  - Letterboxd's Top 500 Films
  - Top 250 Films with the Most Fans
  - Top 250 Animated Films
  - Top 250 Horror Films
  - Top 250 Documentary Films
  - Top 250 Films by Women Directors
  - Top 250 Films by Black Directors
  - Top 100 Underseen Films
- **FR-002**: The system MUST record, per showtime, which specific
  onboarded list(s) its movie matched (not merely that it matched "a"
  list), consistent with feature 003's per-list-key caching already in
  place internally.
- **FR-003**: The system MUST refresh each onboarded list's cached film
  membership on the same schedule as the existing best-of list refresh,
  and MUST NOT let a fetch failure for one onboarded list block the
  refresh of, or clear the cached membership of, any other list.
- **FR-004**: The system MUST surface the matched list name(s) — not a
  generic "best-of list" label — in the recommendation reason shown to
  the operator in the showtime web view.
- **FR-005**: Adding a newly onboarded list to the built-in set MUST
  remain a code change rather than an operator-facing configuration
  option, consistent with feature 003's FR-010 decision to keep the set
  fixed.
- **FR-006**: The system MUST continue to treat "on any onboarded list"
  as one of the existing recommendation criteria (alongside watchlist and
  rating threshold) — a movie need only match one onboarded list to
  qualify a showtime as recommended, per feature 003's existing FR-002/
  FR-011 logic.

### Key Entities

- **Onboarded Official List**: An extension of feature 003's existing
  "built-in best-of list" concept — a named Letterboxd official list
  (name + source URL), each with its own independently cached set of
  matched film slugs, refreshed and treated as a distinct recommendation
  criterion input.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The operator can identify, for any recommended showtime,
  every specific official Letterboxd list its movie appears on, directly
  from the showtime listing, without consulting logs or the database.
- **SC-002**: A movie that only ranks on a newly onboarded list (and no
  other existing criterion) is correctly surfaced as recommended after
  the next scheduled recommendation evaluation, with no manual
  intervention or redeploy required beyond the one-time code change that
  onboarded the list.
- **SC-003**: A temporary fetch failure against any single onboarded
  list's Letterboxd page never removes previously cached recommendations
  that depended on that list, and never prevents the other onboarded
  lists from refreshing on schedule.

## Assumptions

- The additional lists being onboarded are, like the existing Top 250
  list, narrative-feature-film rankings suitable for matching against
  this app's movie showtimes (not TV/miniseries/short-film lists, which
  fall outside this app's scope per feature 002).
- The existing scraping approach (curl_cffi Firefox impersonation,
  paginated poster-grid parsing) works unmodified against every
  additional onboarded list's page, since they share the same Letterboxd
  list-page template as the existing Top 250 list.
- "Recommendation filters" in the feature request means the existing
  best-of-list recommendation criterion (a movie qualifies a showtime as
  recommended by appearing on any onboarded list), not a new
  operator-facing UI control to selectively enable/disable individual
  lists — consistent with feature 003's fixed-set, code-change-to-add
  design (FR-010/FR-005 above).
- Refresh cadence, retry/backoff behavior, and failure handling for each
  onboarded list reuse feature 003's existing best-of list refresh
  mechanism unchanged; this feature only grows the set of lists fed into
  that mechanism and how the results are labeled.
