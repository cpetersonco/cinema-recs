# Phase 0 Research: Cinepolis McKinney Showtime Ingestion

## Decision: Cinepolis' own GraphQL API via a stealth-Playwright-loaded session

**Rationale**: Cinepolis' own website was chosen as the data source
(clarified in spec.md). Getting real data from it required working
through three layers, confirmed empirically against the live site:

1. Plain `requests` is blocked by Cloudflare's bot-protection challenge
   ("Sorry, you have been blocked" interstitial).
2. Default headless Chromium (via Playwright) is *also* blocked by the
   same Cloudflare challenge — a real browser alone isn't sufficient.
   Adding `playwright-stealth` evasions plus a realistic desktop
   user-agent does clear the challenge.
3. Even once past Cloudflare, the site's showtime data isn't in
   server-rendered HTML at all — `cinepolisusa.com` is a Vue/Quasar SPA
   that fetches showings from a GraphQL endpoint (`/graphql`) at
   runtime. DOM scraping is therefore a dead end regardless of bot
   protection; the real integration point is that API.

The GraphQL endpoint itself has an application-level authorization check
independent of Cloudflare: requests must carry `site-id` and `circuit-id`
headers (168 and 89 respectively for Cinepolis McKinney, found via
network inspection) or it returns a permission error. Critically, calls
made through a separate HTTP client — including Playwright's own
`page.request` API context — are still Cloudflare-blocked; only a
`fetch()` executed *from within* the already-loaded page's own JS
context (via `page.evaluate`) succeeds, because it carries the real
browser's TLS/JS fingerprint. The final approach: use stealth Playwright
to load `https://www.cinepolisusa.com/mckinney/showtimes` once, then run
an in-page `fetch()` against `/graphql` with the `showingsForDate` query
and the required headers, and parse the returned JSON directly (no HTML
parsing needed at all — `BeautifulSoup4` is no longer a dependency).

One known limitation: the `showingsForDate` query returns a `screenId`
but no human-readable format/auditorium label (e.g. "4DX"/"VIP").
Resolving that would need a separate screens/auditoriums lookup not
pursued here; `format` is left `None` for now (already optional/nullable
per FR-003 and the data model).

**Alternatives considered**:
- Plain `requests` + `BeautifulSoup4`: rejected — blocked by Cloudflare.
- Default headless Playwright + `BeautifulSoup4`: rejected — also
  blocked by Cloudflare, and even if it weren't, there's no showtime
  markup in the DOM to scrape (SPA renders client-side from the API).
- Calling the GraphQL API directly via `requests`/`urllib` or Playwright's
  `page.request` context (bypassing the browser-driven page load
  entirely): rejected — confirmed via direct testing that these get
  Cloudflare-blocked even with valid session cookies; only fetches
  executed inside a live, stealth-loaded page succeed.
- A third-party ticketing aggregator API: rejected by the spec
  clarification — the operator chose Cinepolis' own site as the
  authoritative source, and a working path into it was found.

## Decision: Ticket URL (FR-011) is constructed from the existing `id` field — no new API/scrape needed

**Rationale**: FR-011 (added via a later clarification session — see spec.md)
requires capturing a per-showing ticket-purchase URL when available.
Two things were confirmed live against the real site:

1. The `showingsForDate` GraphQL query has no URL-shaped field on its
   `Showing` type — a probe of 15 plausible field names (`bookingUrl`,
   `ticketUrl`, `purchaseUrl`, `checkoutUrl`, etc.) all returned GraphQL
   schema errors ("Field '<name>' doesn't exist on type 'Showing'"), and
   introspection (`__type`) is disabled in production.
2. However, the site's own "buy tickets" flow doesn't need one either:
   clicking a showing button in a real (stealth-Playwright) browser
   session navigates the SPA to
   `https://www.cinepolisusa.com/mckinney/checkout/seats/{id}` — where
   `{id}` is exactly the same `id` value already present in every
   `showingsForDate` response entry (verified against 3 separate
   showings, e.g. GraphQL `id: "1644972"` → checkout URL
   `.../checkout/seats/1644972`). The scraper already receives this
   `id`; `parse_showings_response` simply discards it today.

The ticket URL is therefore a pure string template —
`f"https://www.cinepolisusa.com/{location_slug}/checkout/seats/{id}"` —
computed locally from data already fetched, requiring **no new network
call, no new Playwright interaction, and no change to the GraphQL
query**. `location_slug` ("mckinney") is already known — it's embedded
in the cinema's configured `source_url`.

**Risk accepted**: This is an undocumented, reverse-engineered client
route (same category of risk as the GraphQL API itself, per the
Complexity Tracking entry above) — Cinepolis could change this URL
scheme without notice. If a constructed URL ever 404s, that's a silent
staleness risk the operator would only notice by clicking it; no
validation call is made against the URL before storing it (validating
would require a full checkout-flow page load per showing, which is far
more expensive than the ingestion budget allows for a "nice to have"
link). This mirrors FR-011's own "leave it absent rather than fabricating"
framing loosely, but here the construction is confirmed against real
observed behavior, not guessed — the risk is drift over time, not
present-day fabrication.

**Alternatives considered**:
- Reverse-engineering a booking URL via GraphQL introspection: rejected
  — introspection is disabled on this endpoint.
- Loading each showing's checkout page via Playwright during ingestion to
  confirm/validate the URL live: rejected — would multiply ingestion's
  Playwright page-load count by the number of showings captured (dozens
  per run), blowing well past the existing ~30s ingestion performance
  goal for a non-critical enhancement.
- Leaving `ticket_url` unimplemented / always `NULL`: rejected — the
  operator explicitly asked for it (feature 004's driving request), and
  a working construction was found with no added runtime cost.

## Decision: SQLite for storage

**Rationale**: Single cinema, low data volume (tens to low hundreds of
showtimes). SQLite requires no separate database service, persists as one
file that maps cleanly onto an Unraid volume mount, and needs zero extra
container in the Docker Compose setup — directly serving the Simplicity
and Unraid Runtime Compatibility principles.

**Alternatives considered**:
- PostgreSQL/MySQL: rejected as unnecessary operational overhead (a
  second container/service) for this data scale.
- Flat files (JSON/CSV): rejected — reconciliation (dedup, stale-removal)
  is much simpler with basic SQL queries and unique constraints than
  hand-rolled file diffing.

## Decision: In-process scheduling via `APScheduler`

**Rationale**: Running the recurring ingestion job (every 2-4 hours, per
clarification) inside the same process as the web view avoids needing a
separate cron container or host-level cron entry, which would violate the
Docker-native/Unraid principles (no dependency on host scheduling). A
single container that both serves the view and runs its own background
job is the simplest deployable unit.

**Alternatives considered**:
- Host-level cron calling into the container: rejected — depends on
  Unraid host configuration outside the container, contradicting
  Docker-Native Deployment.
- A separate "worker" container plus a "web" container: rejected as
  premature multi-service architecture for this scale (Simplicity
  principle).

## Decision: Flask for the minimal listing view

**Rationale**: FR-010 requires only a simple, human-readable listing of
ingested showtimes — not a rich interactive UI. Flask + a single Jinja2
template is minimal, well-understood, and keeps dependencies light.

**Alternatives considered**:
- FastAPI: reasonable alternative, but its main benefits (async, typed
  request/response schemas, auto-generated OpenAPI) aren't needed for a
  single internal listing page; Flask is simpler for this scope.
- Static HTML file regenerated on each ingestion run (no web framework at
  all): considered but rejected because it would still need a tiny HTTP
  server to be viewable over the network on Unraid, and a run-health
  view benefits from being dynamically rendered.

## Decision: `pytest` with fetch/parse kept separate for testing

**Rationale**: `pytest` is the standard Python test runner. The scraper
module keeps `fetch_showings_json()` (Playwright + network I/O) and
`parse_showings_response()` (pure JSON-to-dataclass mapping) as separate
functions, so unit tests exercise the parser against small hand-built
JSON fixtures (modeled on the real API's schema) without launching a
browser or depending on network access or the live API's current content.

**Alternatives considered**:
- Live network calls in tests: rejected — flaky, slow, and breaks CI/local
  runs whenever Cinepolis changes their API or is unreachable.
- Mocking at the HTTP-library level (e.g. `responses`): not applicable
  here since the real fetch happens via an in-page `fetch()` call inside
  a Playwright-controlled browser, not a Python HTTP client — there is no
  Python-level HTTP call to intercept in `fetch_showings_json()` itself.
