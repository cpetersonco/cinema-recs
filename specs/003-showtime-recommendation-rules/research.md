# Phase 0 Research: Showtime Recommendation Rules

## Decision: Plain `requests` against Letterboxd's public pages (no headless browser, no HTML-parsing library)

**Rationale**: Live checks against `letterboxd.com` (film pages, `/tmdb/{id}/` redirect,
watchlist pages, and a curated list page) all returned `200`/`302` with a
default `requests` session — no Cloudflare bot-challenge, no custom
User-Agent, no cookies needed (unlike feature 001's Cinepolis target).
The three page types this feature needs are all parseable with plain
`re`/`json` against small, stable markers already present in the HTML:

- `letterboxd.com/tmdb/{tmdb_id}/` — a `302` redirect whose `Location`
  header is `/film/{slug}/`. This is the FR-012 "translation surface"
  lookup; a non-redirect response (e.g. `404`) means no Letterboxd page
  exists for that TMDB id.
- `letterboxd.com/film/{slug}/` — contains a
  `<script type="application/ld+json">` block (wrapped in a `CDATA`
  comment) with `"aggregateRating":{"ratingValue":4.23,...}` — directly
  parseable via `json.loads` after stripping the CDATA wrapper.
- `letterboxd.com/{username}/watchlist/` and
  `letterboxd.com/{list-author}/list/{slug}/` — both paginated poster
  grids where each film's link is `data-target-link="/film/{slug}/"`.
  Pagination is `.../page/{n}/`, with the highest page number visible in
  the first page's pagination links.

**Alternatives considered**:
- Stealth Playwright (feature 001's approach): rejected — no bot
  protection was encountered against any of the three page types, so a
  headless browser would add container weight/latency for no benefit,
  same reasoning as feature 002 rejecting Playwright for TMDB.
- `BeautifulSoup4`: rejected — the three data points needed (redirect
  target, JSON-LD rating, `data-target-link` slugs) are all extractable
  with small `re` patterns and stdlib `json`, so a full HTML parser isn't
  needed, consistent with the Simplicity principle. This is a
  documented fragility tradeoff (see Risks below), same category as
  feature 001's placeholder-selector gap.

## Decision: A dedicated `letterboxd.com/search/...` lookup is NOT used

**Rationale**: `letterboxd.com/search/lists/...` returned `403` in live
testing (unlike the film/list/watchlist pages, which all returned `200`).
This feature never needs Letterboxd's search at runtime anyway — the
watchlist URL is built from the configured username, and best-of list
URLs are a fixed, hardcoded set (FR-010) resolved once during this
planning phase, not discovered dynamically.

## Decision: Built-in best-of list URL for "Official Top 250 Narrative Feature Films"

**Rationale**: Verified live at
`https://letterboxd.com/ctsearles/list/official-top-250-narrative-feature-films/`
(`200`, 3 pages, `data-target-link` slugs present, e.g. `/film/parasite-2019/`,
`/film/the-godfather/`). This is a widely-cited community-maintained
clone of Letterboxd's own "Official Top 250" ratings-based ranking (the
list is not hosted under Letterboxd's own `letterboxd.com/official/`
curator account, which hosts a different set of editorial lists) — but it
is the standard reference for this specific named list. Per FR-010, this
URL is a hardcoded Python constant; if this particular clone disappears
or a better-maintained one emerges, swapping the URL is a one-line code
change, not a config change.

**Alternatives considered**:
- `letterboxd.com/official/...`: checked directly — Letterboxd's own
  curator account hosts different editorial lists (e.g. "Top 250 Films of
  the 2020s"), not this specific list by this exact name.
- An operator-configurable list of URLs: explicitly rejected by the
  spec's Clarifications session (fixed, built-in set only).

## Decision: Resolving an apparent conflict between FR-003(c) and FR-005/SC-004

**The conflict**: FR-003(c) says a showtime is recommended whenever its
movie appears on a built-in best-of list — unconditionally, with no
mention of needing any configuration. FR-005 and SC-004, plus the
"Edge Cases" section, say that with *no* Letterboxd username *and* no
rating threshold configured, **zero** showtimes must ever be recommended
— which would require gating the best-of-list criterion too, since it's
otherwise always-on.

**Resolution**: All three criteria (watchlist, rating, best-of list) are
gated behind at least one of {`LETTERBOXD_USERNAME`,
`LETTERBOXD_RATING_THRESHOLD`} being configured. With genuinely zero
configuration, recommendation evaluation short-circuits to "nothing
recommended" without even checking best-of-list membership. As soon as
either one is set, all three criteria (including best-of list) become
active. This satisfies FR-005/SC-004/the edge case literally (zero config
→ zero recommendations) while keeping FR-003(c)'s best-of-list check
active in the normal case where the operator has configured anything at
all — the "no criteria active" framing in FR-005 is read as "the operator
hasn't engaged with this feature yet," not "each criterion must be
individually configured."

**Alternatives considered**:
- Best-of list always active regardless of other config: rejected —
  directly contradicts FR-005/SC-004's explicit zero-config guarantee.
- Best-of list requiring its own separate opt-in flag: rejected — not
  supported anywhere in the spec/FRs; adds configuration surface FR-010
  doesn't ask for.

## Decision: Config takes effect via container restart, not live-reload

**Rationale**: Per the project's established env-var-driven config
pattern (features 001/002) and the constitution's Unraid conventions, an
operator changes `LETTERBOXD_USERNAME`/`LETTERBOXD_RATING_THRESHOLD` via
Unraid's env var UI and restarts the container — this is neither a
"rebuild" (no new image) nor a "redeploy" (same container definition), so
it satisfies FR-007/US3's "without requiring the application to be
rebuilt or redeployed." No dynamic config-reload mechanism (e.g. a
settings file watched for changes) is needed — that would be
over-engineering relative to the Simplicity principle for a
single-operator project already comfortable editing env vars.

**Alternatives considered**:
- A runtime settings API/file watcher: rejected — no concrete need stated
  in the spec beyond "no rebuild/redeploy," which a restart-on-env-change
  workflow already satisfies.

## Decision: Invalid rating threshold parsing (FR-008)

**Rationale**: `LETTERBOXD_RATING_THRESHOLD` is optional and parsed
leniently — an unset or non-numeric value is treated as "no threshold
configured" (logged once as a warning if a value was present but
unparseable), never as a fatal config error. This mirrors FR-008
verbatim and contrasts with `TMDB_API_KEY` (feature 002), which is
required and fails startup if missing — here, the whole point is that a
missing/invalid value degrades gracefully to "fewer active criteria,"
not "no enrichment can happen at all."

## Decision: Recommendation evaluation runs on the same schedule as ingestion/enrichment

**Rationale**: FR-002/FR-007/SC-002 require re-evaluation whenever new
showtimes arrive or the watchlist changes, "within one evaluation cycle,"
without rebuild/redeploy. The app already has an `APScheduler` interval
job (`scheduler.py`) driving periodic ingestion. This feature extends
that same job (and the equivalent one-shot startup call in `main.py`) to
also run enrichment and recommendation evaluation each cycle. Feature
002 only wired enrichment into `main.py`'s one-shot call, not
`scheduler.py`'s periodic job — that gap is closed as part of this
feature's work, since without periodic enrichment, this feature's
periodic re-evaluation requirement can't be met for movies ingested after
startup.

**Alternatives considered**:
- A separate, independently-configured refresh interval for
  recommendation evaluation: rejected — adds a second interval knob for
  no concrete benefit; reusing `CINEMA_RECS_REFRESH_INTERVAL_HOURS`
  keeps one config surface, consistent with Simplicity.

## Decision: Cache per-movie Letterboxd data (slug + rating); always re-fetch watchlist/best-of-list membership

**Rationale**: A movie's Letterboxd slug and average rating are fetched
once per movie and cached (mirrors feature 002's TMDB metadata caching
— same "look up once, cache forever" pattern for data that changes
slowly). Watchlist and best-of-list *membership*, by contrast, are
re-fetched in full every evaluation cycle, since FR-007/SC-002 explicitly
require reacting to watchlist changes — caching those would defeat the
feature's purpose. Per the spec's resilience edge case, a failed
watchlist/list re-fetch leaves the previously cached membership set
untouched (logged, not treated as "empty") rather than wiping it.

**Alternatives considered**:
- Also re-fetching each movie's rating every cycle: rejected as
  unnecessary request volume for a value that changes slowly; if this
  proves too stale in practice, a follow-up decision, not a blocker here.

## Risks

- The `re`/`json`-based scraping (no HTML parser) is coupled to
  Letterboxd's exact current markup (JSON-LD block wrapper, `data-target-link`
  attribute name) — if Letterboxd changes these, extraction breaks
  silently until noticed via logs. Documented and accepted, consistent
  with feature 001/002's precedent of accepting scraping fragility for a
  personal project rather than adding parsing-robustness machinery.
