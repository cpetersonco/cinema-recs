# Phase 0 Research: Movie Metadata Enrichment via TMDB

## Decision: Plain `requests` against TMDB's public REST API

**Rationale**: Unlike feature 001's Cinepolis target, TMDB is a normal,
documented, non-bot-protected public REST API (`api.themoviedb.org/3`)
intended for exactly this kind of programmatic access. A headless
browser (as feature 001 needed to clear Cloudflare) would be pure
unneeded overhead here.

**Alternatives considered**:
- Reusing Playwright for this too: rejected — no bot protection to
  clear, so a browser adds container weight and latency for no benefit.
- A TMDB-specific Python SDK (e.g. `tmdbsimple`): rejected — the API
  surface needed here (search + movie detail) is small enough that a
  thin wrapper over `requests` is simpler than adopting a third-party
  SDK dependency, consistent with the Simplicity principle.

## Decision: Fixed-delay pacing instead of a rate-limiting algorithm

**Rationale**: TMDB's request volume here is bounded by the number of
distinct new movies per ingestion cycle (typically single digits to low
tens for one cinema) — nowhere near needing a sliding-window or
token-bucket rate limiter. A simple fixed delay between sequential
requests (e.g. a few hundred milliseconds) keeps requests well-paced
without added complexity.

**Alternatives considered**:
- A proper token-bucket/sliding-window rate limiter: rejected as
  over-engineered for this request volume; adds a dependency or
  nontrivial custom code for a problem a `time.sleep()` between calls
  already solves at this scale.

## Decision: `unittest.mock.patch` (stdlib) for testing TMDB calls

**Rationale**: Only a handful of HTTP call sites need mocking (search,
detail fetch). The standard library's `unittest.mock` is sufficient and
avoids adding a new test-only dependency, unlike feature 001's original
plan to use `responses` (which became moot once the scraper's fetch
moved to an in-page Playwright `fetch()` with no Python-level HTTP call
to intercept).

**Alternatives considered**:
- `responses` library: rejected — adds a dependency for a need
  `unittest.mock.patch` already covers at this scale.

## Decision: Naive title-similarity matching (normalized exact / clear top result)

**Rationale**: Per spec Assumptions, matching uses TMDB's `/search/movie`
endpoint and accepts the top result only when it's a clearly-best match:
normalized (case/punctuation-insensitive) title equality, optionally
cross-checked against release year when the cinema source provides one.
If the top two results are close in popularity/vote count with similar
titles, or no result closely matches the title at all, the movie is
recorded unmatched (per FR-004) rather than guessing. This mirrors the
"good-enough default, document the gap" precedent set by feature 001
(e.g., its scraper's placeholder selectors, its `format` field gap).

**Alternatives considered**:
- A fuzzy-matching library (e.g. `rapidfuzz`, `thefuzz`): rejected for
  this phase — adds a dependency for a refinement that isn't needed yet;
  if real-world mismatch rates prove the naive approach insufficient,
  that's a follow-up decision, not a blocker for this plan.
- Always accepting TMDB's top search result unconditionally: rejected —
  this is exactly the "silently wrong metadata" failure mode FR-004 and
  User Story 2 explicitly guard against.

## Decision: TMDB identifier as the sole hand-off to feature 003

**Rationale**: Per FR-009 and the Clarifications session, this feature's
only obligation toward feature 003 is storing an accurate TMDB
identifier per matched movie. Feature 003 is responsible for its own
Letterboxd resolution (`letterboxd.com/tmdb/{tmdb_id}/`) using that ID —
this feature does not call Letterboxd itself, keeping the two features'
concerns cleanly separated (TMDB display metadata vs. Letterboxd
recommendation signals) even though a dependency now exists between
them.

**Alternatives considered**:
- This feature also resolving and storing the Letterboxd URL/ID itself:
  rejected — that's feature 003's concern (per its own spec/plan) and
  would blur the boundary between "TMDB enrichment" and "Letterboxd
  recommendation data"; this feature's job ends at providing a reliable
  TMDB identifier.
