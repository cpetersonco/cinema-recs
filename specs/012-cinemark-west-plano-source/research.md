# Research: Cinemark West Plano XD and ScreenX Showtime Ingestion Source

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## 1. Site Platform & Fetch/Parse Method

### Decision
Fetch showtimes from Cinemark's own first-party, server-rendered HTML partial endpoint:

```
GET https://www.cinemark.com/umbraco/surface/Showtimes/GetByTheaterId?theaterId=231&showDate=YYYY-MM-DD
```

one call per published show date, walking the venue's own date-tab list (see §4) rather than
scraping the full theatre page.

### Rationale
- Confirmed via live browser network inspection (2026-07-23) against
  `https://www.cinemark.com/theatres/tx-plano/cinemark-west-plano-xd-and-screenx`: clicking a
  date tab issues `GET /umbraco/surface/Showtimes/GetByTheaterId?theaterId=231&showDate=2026-08-02`
  (HTTP 200) and swaps the showtimes list in place — this is Cinemark's Umbraco CMS ("surface
  controller") backing the date-tab widget.
- The endpoint returns fully server-rendered HTML for that single date (verified by fetching it
  directly in a new tab and reading its text/DOM) — not JSON, and not an empty SPA shell. No
  client-side JavaScript execution is required to obtain the showtime data itself, unlike
  Angelika Dallas (spec 008, React SPA + gated JSON API).
- `theaterId=231` is West Plano's fixed identifier, visible in the endpoint URL and in every
  `TicketSeatMap` link on the page — hardcode it as a constant, matching the
  `ANGELIKA_DALLAS_CINEMA_ID` / `TEXAS_THEATRE_*` precedent.
- No CORS/WAF rejection was observed fetching this endpoint directly (unlike Angelika's `/films`
  API); however, per [[project_curl_cffi_letterboxd_fix]] and
  [[project_curl_cffi_could_replace_playwright]], other Cinemark-adjacent or Cloudflare-fronted
  sites in this project have needed TLS impersonation or a real browser to avoid bot-detection
  blocking plain `httpx`/`curl` requests even when no explicit auth is required. Given this is
  unconfirmed for Cinemark specifically (the browser-based check used a real Chrome session),
  the implementation MUST fetch via the existing Playwright + `playwright-stealth` browser
  session already used for Texas Theatre and Cinepolis (`REALISTIC_USER_AGENT`,
  `Stealth().apply_stealth_sync`), reusing `_fetch_page_html_with_retry`'s retry/blocked-page
  pattern, rather than introducing a new plain-`httpx` or `curl_cffi` fetch path for this one
  source. This keeps fetch behavior consistent across all sources (Simplicity principle) and
  avoids re-litigating the deferred curl_cffi refactor as part of this feature.

### Alternatives Considered
- **Plain `httpx`/`requests` GET (no browser)**: Simpler and faster if it works, and nothing
  observed during manual browser inspection proves it wouldn't — but it was not verified
  headless/unauthenticated (the check used a logged-out but full Chrome session with normal
  headers/TLS fingerprint). Rejected for this feature to avoid shipping an unverified fetch path;
  can be revisited as a follow-up optimization once proven against a real headless request,
  consistent with the deferred curl_cffi migration already noted in project memory.
- **Scraping the full theatre page (`/theatres/tx-plano/...`) and letting its embedded default
  date render**: Works for "today" only; would require simulating date-tab clicks via Playwright
  DOM interaction for every other date instead of calling the underlying endpoint the site itself
  calls. Rejected — hitting the surface-controller endpoint directly for each date is simpler and
  mirrors the "call what the page calls" precedent set by Angelika Dallas.

---

## 2. Presentation Format Extraction (including 70mm)

### Decision
Two distinct extraction paths are required, confirmed via live inspection of the
`GetByTheaterId` HTML fragment:

1. **70mm is encoded as a separate movie listing, not a format tag.** "The Odyssey" (standard/XD/
   ScreenX/3D showtimes, `CinemarkMovieId=108919`) and "The Odyssey 70mm" (70mm-only showtimes,
   `CinemarkMovieId=110535`) appear as two independent `<article>`-level listings on the same
   date, each with its own poster, title, and showtime groups. The 70mm listing's title literally
   ends in `" 70mm"` and its one showtime group is tagged with a plain-text label `"70mm"` (no
   icon). The scraper MUST detect a movie title ending in `" 70mm"` (case-insensitive, trimmed),
   strip that suffix to recover the base film title (e.g. `"The Odyssey"`), and tag every
   showtime under that listing with `format="70mm"` — satisfying FR-004's requirement that 70mm
   be distinctly, unambiguously tagged rather than merged into "special presentation."
2. **XD, ScreenX, D-BOX, and RealD 3D are encoded as `<img alt="...">` badges** inside a small
   `<ul>` immediately preceding each showtime-group's amenity list (e.g. `<img alt="Cinemark XD">`,
   `<img alt="D-BOX">`, `<img alt="ScreenX">`, `<img alt="RealD 3D">`). A group with no such badge
   and only a `"Standard Format"` text listitem (or nothing) is Standard. Groups can carry more
   than one badge at once (e.g. XD + D-BOX together on the same showtime group, confirmed live) —
   the scraper MUST capture all badges present on a group and combine them into a single format
   value (e.g. `"XD+D-BOX"` or a similar deterministic join) rather than only taking the first.

### Rationale
- Confirmed directly from the fetched HTML fragment (`GetByTheaterId?...&showDate=2026-07-24`):
  "The Odyssey" and "The Odyssey 70mm" are sibling listings with different `CinemarkMovieId`
  values and independent showtime groups, not one listing with a 70mm-tagged subgroup.
- Badge `alt` text (`"Cinemark XD"`, `"D-BOX"`, `"ScreenX"`, `"RealD 3D"`) is a clean, stable
  signal — same pattern as Angelika's structured `showtypes[].type` field (research.md §2 there),
  just conveyed via image alt text instead of a JSON field.

### Alternatives Considered
- **Treating "The Odyssey 70mm" as an unrelated movie and leaving the title as-is**: Rejected —
  it would surface as a separate, oddly-named "movie" in recommendations rather than a 70mm
  screening of "The Odyssey," directly undermining US2/FR-004, which is this feature's primary
  motivation.
- **Regex-parsing format out of the movie title for XD/ScreenX/D-BOX/3D (Texas Theatre style)**:
  Not needed — the badge `alt` text is already structured and reliable, unlike Texas Theatre's
  freeform event titles.

---

## 3. Ticket URL & Showtime Identity

### Decision
Extract the ticket URL directly from each showtime's own anchor `href`
(`/TicketSeatMap/?TheaterId=231&ShowtimeId={id}&CinemarkMovieId={id}&Showtime={iso}[&LinkedShowtimeId={id}]`)
and resolve it against `https://www.cinemark.com`. No URL construction/guessing is required — it
is already present, complete, and film/showtime-specific in the markup (`ShowtimeId` uniquely
identifies each individual showtime).

### Rationale
- Directly observed in the fetched fragment; matches the precedent set by Cinepolis (`Decision:
  Ticket URL (FR-011) is constructed from the existing id field — no new API/scrape needed`) of
  preferring an already-present identifier over hand-built URLs.

---

## 4. Date Window Discovery

### Decision
Discover the exact set of published show dates from the main theatre page's own date-tab strip
(`a.showdate-link[data-datevalue="YYYY-MM-DD"]`, plus the implicit "Today" tab), and fetch
`GetByTheaterId?theaterId=231&showDate=...` once per date in that list — rather than guessing a
fixed number of days forward.

### Rationale
- Confirmed live: the date-tab strip on the West Plano page currently lists ~75 dates (today
  through October 21, 2026), each carrying its own `data-datevalue` attribute — this is the
  site's own authoritative statement of "every date we currently have a schedule for," exactly
  analogous to Angelika Dallas's `#anytime span` date strip (research.md §1 there) and Texas
  Theatre's "next month" link walk (research.md §2 there). All three existing/new sources follow
  the same principle: walk the site's own enumeration of its published window rather than
  hardcoding an assumed number of days/months.
- This window (~13 weeks) is expected to fluctuate as Cinemark adds/removes future dates; reading
  it fresh on every ingestion run (rather than caching it) keeps the source correct without extra
  logic.

### Alternatives Considered
- **Fixed N-day walk (e.g. 14 or 30 days) via `showDate` regardless of the tab strip**: Simpler
  but risks either missing dates the site has already published beyond N days, or wastefully
  querying dates beyond the site's real window. Rejected in favor of reading the site's own
  authoritative list, consistent with the other two sources.

---

## 5. Timezone & DateTime Handling

### Decision
Parse each showtime's `Showtime=` query-string value from the `TicketSeatMap` href (e.g.
`2026-07-24T08:00:00`, a naive local timestamp with no UTC offset) as wall-clock Central Time
(`America/Chicago`), reusing the existing `CENTRAL_TIME` `ZoneInfo` constant already defined in
`scraper.py`. No offset normalization is needed (unlike Angelika's `-05`/`-05:00` fix) since the
value carries no offset at all — it is inherently local.

### Rationale
- Confirmed live: `Showtime=2026-07-24T08:00:00` matches the on-page displayed time (8:00am)
  exactly, with West Plano being a Plano, TX (Central Time) venue.

---

## 6. Non-Film Events

### Decision
No special classification/filtering logic is implemented in this feature. Every listing observed
in the `GetByTheaterId` fragment (including subtitled international films and stage/opera-style
event titles like "Hadestown: The Musical") shares the identical markup shape as a standard film
listing, with no distinguishing "event type" flag in the HTML. Per the spec's Assumptions section,
such listings are ingested as regular screenings; distinguishing true non-film one-off events
(e.g. a future Met Opera broadcast) is deferred until a concrete data-quality problem is observed,
consistent with the Simplicity principle.

### Rationale
- No structural signal to filter on was found during live inspection; inventing a heuristic
  (e.g. title keyword matching) without an observed need would be speculative, which the project
  constitution's Simplicity & Solo-Maintainer Ergonomics principle discourages.

### Alternatives Considered
- **Keyword-based filtering (e.g. exclude titles containing "Opera", "Anniversary")**: Rejected
  as premature — no non-film listing was present in the sampled dates to validate such a
  heuristic against, and false-positive risk (excluding a legitimately-titled film) is real.

---

## 7. Deduplication & Idempotency

### Decision
Identify unique showtimes using the same tuple `(cinema_id, movie_title, show_date, start_time)`
convention used by every existing source (with the 70mm-stripped title from §2 as `movie_title`
for 70mm showtimes), and reuse `storage.upsert_showtime` / `storage.mark_stale_showtimes`
unchanged.

### Rationale
- Established, shared dedup contract across Cinepolis, Texas Theatre, and Angelika Dallas — no
  new behavior is required; this source only needs to emit `ScrapedShowtime` records in the
  existing shape.
