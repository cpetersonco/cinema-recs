# Feature Specification: Showtime Recommendation Rules

**Feature Branch**: `003-showtime-recommendation-rules`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Recommendation logic itself — some rule (genre preference, rating threshold, "new release") that actually picks which showtimes to surface, using #1 as input."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get recommended showtimes based on Letterboxd signals (Priority: P1)

As the operator, I want the system to mark a showtime recommended when
its movie is on my Letterboxd watchlist, has a high Letterboxd rating, or
appears on one of Letterboxd's official best-of lists, so I can surface
re-releases and revivals I'd likely enjoy in time to get tickets — I'm
not interested in being flagged about new releases in general.

**Why this priority**: This is the core value of the whole "cinema-recs"
project — everything before this (ingestion) exists to feed this
decision. Without it, showtimes are just a list, not a recommendation.

**Independent Test**: Can be fully tested by configuring a Letterboxd
username with a known watchlist, ingesting a showtime for a movie on
that watchlist, and confirming it's marked recommended, while a showtime
for an unrelated movie is not.

**Acceptance Scenarios**:

1. **Given** a showtime's movie is on the operator's configured
   Letterboxd watchlist, **When** recommendations are evaluated, **Then**
   that showtime is marked recommended.
2. **Given** a rating threshold is configured and a showtime's movie's
   Letterboxd average rating exceeds that threshold, **When**
   recommendations are evaluated, **Then** that showtime is marked
   recommended.
3. **Given** a showtime's movie appears on one of Letterboxd's official
   best-of lists (e.g., "Official Top 250 Narrative Feature Films"),
   **When** recommendations are evaluated, **Then** that showtime is
   marked recommended.
4. **Given** a showtime's movie matches none of the three criteria
   (not on the watchlist, rating at or below threshold, not on a
   tracked list), **When** recommendations are evaluated, **Then** that
   showtime is not marked recommended.

---

### User Story 2 - See recommended showtimes at a glance (Priority: P2)

As the operator, I want the existing showtime listing view to visually
distinguish recommended showtimes from the rest, so I can quickly spot
what's worth seeing without reading every row's metadata myself.

**Why this priority**: Recommendations only deliver value once visible;
this is the smallest change that surfaces the P1 logic.

**Independent Test**: Can be fully tested by ingesting/enriching a movie
that matches a configured preference and confirming its showtime is
visually marked as recommended in the listing view, while non-matching
showtimes are not.

**Acceptance Scenarios**:

1. **Given** a showtime is marked recommended, **When** the operator
   views the listing, **Then** it is visually distinguished (e.g., a
   badge or highlight) from non-recommended showtimes.
2. **Given** no showtimes currently match any configured preference,
   **When** the operator views the listing, **Then** the listing still
   displays normally with none marked recommended, rather than showing an
   error or empty page.

---

### User Story 3 - Update rating threshold and see recommendations change (Priority: P3)

As the operator, I want to adjust my rating threshold and have
recommendations reflect the change on the next evaluation, without
needing a code change or redeployment. (The watchlist and best-of list
criteria update naturally on their own: the watchlist reflects whatever
is currently on the operator's Letterboxd watchlist, and the best-of
lists are a fixed, built-in set — see Clarifications.)

**Why this priority**: Taste changes over time; without this, the
feature would need a code change every time the operator's rating bar
shifts, which doesn't scale even for a single operator.

**Independent Test**: Can be fully tested by changing the rating
threshold, triggering recommendation evaluation again, and confirming
previously recommended showtimes that only matched via rating and no
longer meet the new threshold are unmarked, and newly matching ones are
marked.

**Acceptance Scenarios**:

1. **Given** the rating threshold is changed, **When** recommendations
   are next evaluated, **Then** showtimes that only matched via rating
   and no longer meet the new threshold are no longer marked
   recommended.
2. **Given** the rating threshold is changed, **When** recommendations
   are next evaluated, **Then** the change takes effect without
   requiring the application to be rebuilt or redeployed.
3. **Given** the operator's Letterboxd watchlist changes (a movie is
   added or removed on Letterboxd itself), **When** recommendations are
   next evaluated after the watchlist is re-fetched, **Then** the
   recommendation status of affected showtimes updates accordingly.

---

## Clarifications

### Session 2026-07-22

- Q: Does matching ANY one configured criterion (genre, rating, new release) qualify a showtime as recommended, or must ALL configured criteria be satisfied? → A: ANY criterion matching is sufficient (OR logic across genre preference, rating threshold, and new-release window).
- Q: How should the system obtain the operator's Letterboxd watchlist and list data? → A: Scrape the operator's public Letterboxd profile (watchlist page + relevant list pages) given a configured username, consistent with feature 001's scraping precedent.
- Q: Should the rating threshold use Letterboxd's per-movie rating (0.5-5 scale) or TMDB's existing rating (0-10 scale)? → A: Letterboxd's per-movie average rating, fetched directly from Letterboxd — matches the ">4.8" framing and the Letterboxd-centric criteria; this is a new per-movie data need beyond feature 002's TMDB-only enrichment.
- Q: Should "best-of lists" be a fixed set of Letterboxd's official curated lists, or an operator-configurable set of list URLs? → A: A fixed set of Letterboxd's official curated lists (e.g. "Official Top 250 Narrative Feature Films"), built in rather than configurable; adding a new list is a code change, not a config change.

**Resulting scope pivot**: this feature's recommendation criteria are now
entirely Letterboxd-based (watchlist membership, Letterboxd rating,
official Letterboxd list membership) and no longer include genre
preference or a "new release" window — the operator explicitly does not
want new-release notifications, only surfacing rewatchable/re-release
showings they'd likely enjoy. None of the three Letterboxd-based
criteria themselves require TMDB *data* (genre/rating/release date).

- Q: Should this feature use feature 002's TMDB match to locate a movie's Letterboxd entry, instead of matching the raw scraped title against Letterboxd independently? → A: Yes — feature 002's TMDB identifier is used as a reliable "translation surface" to Letterboxd (Letterboxd's catalog exposes films by TMDB ID). **This corrects the earlier statement in this same session that feature 002 was no longer a dependency**: feature 002 IS a hard dependency of this feature again — not for its genre/rating data, but because its TMDB match is the mechanism this feature uses to resolve the Letterboxd entry in the first place. A movie unmatched in feature 002 cannot be evaluated by any of this feature's three criteria.

### Edge Cases

- What happens when a showtime's movie has no feature-002 TMDB match, or
  has a TMDB match that doesn't resolve to a Letterboxd film page? Either
  way, none of the three criteria can be evaluated with confidence, so it
  is not marked recommended.
- What happens when no rating threshold is configured and the operator's
  Letterboxd username is also not configured? No showtime should ever be
  marked recommended, rather than the system defaulting to marking
  everything or nothing ambiguously.
- What happens when preference configuration itself is invalid (e.g., a
  malformed rating threshold)?
- What happens when the configured Letterboxd profile is private,
  doesn't exist, or is temporarily unreachable? Recommendation
  evaluation must still complete for criteria that don't depend on
  Letterboxd data being reachable at that moment (e.g., a previously
  cached watchlist, or the built-in best-of lists if those are cached
  separately), and the failure should be logged rather than silently
  treated as "watchlist is empty."
- What happens when a movie matches more than one criterion (e.g., it's
  both on the watchlist and highly rated)? The showtime is still marked
  recommended once, but the notification/display should be able to
  surface all matching reasons, not just the first one found.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow the operator to configure: a
  Letterboxd username (to source the watchlist and, implicitly, the
  operator's identity for Letterboxd data) and a minimum Letterboxd
  rating threshold (0.5-5 scale).
- **FR-002**: The system MUST evaluate every ingested showtime's movie
  against the configured criteria whenever ingestion produces new or
  updated showtimes, or whenever the operator's Letterboxd watchlist is
  re-fetched.
- **FR-003**: The system MUST mark a showtime as recommended when its
  movie satisfies at least one of: (a) it is on the operator's
  configured Letterboxd watchlist, (b) its Letterboxd average rating
  exceeds the configured threshold, or (c) it appears on one of
  Letterboxd's built-in official best-of lists (see FR-010). Matching
  any single criterion is sufficient.
- **FR-004**: The system MUST NOT mark a showtime as recommended when its
  movie has no feature-002 TMDB match, or when that TMDB match does not
  resolve to a Letterboxd film page, since none of the three criteria
  can be evaluated with confidence in either case.
- **FR-005**: The system MUST NOT mark any showtime as recommended when
  no Letterboxd username is configured and no rating threshold is
  configured (i.e., no criteria are active).
- **FR-006**: The showtime listing view MUST visually distinguish
  recommended showtimes from non-recommended ones.
- **FR-007**: The system MUST re-evaluate recommendations whenever the
  rating threshold changes, the operator's Letterboxd watchlist changes,
  or new/updated showtime data becomes available, without requiring an
  application rebuild or redeploy.
- **FR-008**: The system MUST treat an invalid rating threshold (e.g.,
  non-numeric) as if that specific criterion were unset, rather than
  failing recommendation evaluation entirely.
- **FR-009**: The system MUST allow the operator to configure a
  Letterboxd username, and MUST retrieve that operator's public
  Letterboxd watchlist by scraping their public profile, consistent with
  feature 001's scraping approach for the cinema source.
- **FR-010**: The system MUST check movies against a fixed, built-in set
  of Letterboxd's official curated lists (at minimum "Official Top 250
  Narrative Feature Films"); adding another built-in list is a code
  change, not something the operator configures.
- **FR-011**: The system MUST record, for each showtime marked
  recommended, which of the three criteria matched (watchlist / rating /
  best-of list — a showtime can match more than one), so that reason can
  be surfaced to the operator wherever the recommendation is shown or
  notified about (see feature 004).
- **FR-012**: The system MUST locate a movie's Letterboxd entry using
  feature 002's already-resolved TMDB identifier for that movie, rather
  than independently matching the raw scraped title against Letterboxd.
  A movie with no feature-002 TMDB match cannot be evaluated by this
  feature at all (per FR-004).

### Key Entities

- **Recommendation Configuration**: A single, operator-wide configuration
  (not per-user, consistent with this being a personal/solo-operator
  project) consisting of: a Letterboxd username and a minimum Letterboxd
  rating threshold (0.5-5 scale).
- **Letterboxd Movie Data**: Per-movie data fetched from Letterboxd,
  located via feature 002's TMDB identifier for that movie (see FR-012):
  average rating, whether it's on the operator's watchlist, and which
  (if any) built-in best-of lists it appears on. Distinct from feature
  002's TMDB-based Movie Metadata, but dependent on it for identifying
  which Letterboxd entry to fetch.
- **Showtime Recommendation Status**: A derived result on each showtime:
  whether it's recommended, and the specific matched reason(s) (one or
  more of: on watchlist, rating above threshold, on a best-of list).
  Computed from the showtime's linked Letterboxd Movie Data and the
  current Recommendation Configuration. Recomputed whenever either input
  changes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After configuring a Letterboxd username and/or rating
  threshold, the operator can identify which currently listed showtimes
  are recommended, and why, without manually checking Letterboxd
  themselves.
- **SC-002**: Changing the rating threshold, or a change to the
  operator's Letterboxd watchlist, is reflected in which showtimes are
  marked recommended within one evaluation cycle, without any code or
  deployment change.
- **SC-003**: No showtime for a movie that can't be matched to a
  Letterboxd film page is ever marked recommended.
- **SC-004**: With no Letterboxd username and no rating threshold
  configured, zero showtimes are marked recommended (no false positives
  from an empty configuration).
- **SC-005**: For every recommended showtime, the operator can see which
  specific criterion (or criteria) caused it to be recommended, not just
  that it was recommended.

## Assumptions

- This is a single-operator personal project (per the project
  constitution); the Recommendation Configuration is one global
  configuration, not per-user profiles or accounts.
- Configuration (Letterboxd username, rating threshold) follows the same
  environment-variable-driven pattern established in feature 001, rather
  than a dedicated settings UI — a settings UI is not precluded but is
  not required for this feature.
- Recommendation evaluation depends on Letterboxd data (the operator's
  watchlist, per-movie ratings, and the built-in best-of lists), fetched
  by scraping public Letterboxd pages. This is a separate scrape target
  from feature 001's cinema-showtime scraping, but it is NOT independent
  of feature 002: locating the correct Letterboxd entry for a movie
  depends on feature 002's TMDB match for that movie (see FR-012).
- The built-in best-of list set starts with "Official Top 250 Narrative
  Feature Films" and can be expanded with additional official Letterboxd
  lists later as a code change.
- A movie's Letterboxd entry is located via its feature-002 TMDB
  identifier (Letterboxd's catalog exposes films by TMDB ID), not by an
  independent title-similarity match against Letterboxd directly. This
  is more reliable than matching the raw scraped title a second time,
  since it reuses feature 002's already-resolved match rather than
  introducing a second independent point of failure — exact lookup
  mechanics are a planning concern, not a specification concern.
