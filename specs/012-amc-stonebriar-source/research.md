# Research: AMC Stonebriar 24 Showtime Ingestion Source

**Feature**: [spec.md](spec.md)

## §1. Live site inspection (constitution VII: Live-Verify External Integrations)

Inspected `https://www.amctheatres.com/movie-theatres/dallas-ft-worth/amc-stonebriar-24/showtime`
(the URL given in the feature input) directly in a real browser and via `curl`.

**Correction to input URL**: The given URL (`/showtime`, singular) 404s — "You've gone off
script". The real showtimes route is plural: `/showtimes`. The correct source URL is:

```
https://www.amctheatres.com/movie-theatres/dallas-ft-worth/amc-stonebriar-24/showtimes
```

**Decision**: Use the plural `/showtimes` URL as `AMC_STONEBRIAR_DEFAULT_URL`.

## §2. Site architecture

**Decision**: Playwright (+ `playwright-stealth`), same as the Angelika Dallas and Texas Theatre
integrations — plain HTTP requests do not work against this source.

**Rationale**:
- `amctheatres.com` is a Next.js (App Router / React Server Components) site — page navigations in
  the browser fetch `?_rsc=<id>` payloads for prefetched links, and the showtimes content itself
  arrives inline in the server-rendered document for the page actually navigated to (no standalone
  JSON showtimes XHR/fetch was observed in captured network traffic).
- Critically, a plain `curl` request (realistic desktop User-Agent) to the showtimes URL returns
  `HTTP/2 302` redirecting to `queue.amctheatres.com` — a Cloudflare-integrated bot/"safety net"
  gate (`e=globalsafetynetweb`, `kupver=cloudflare-4.4.3`) — before any page content is served. A
  real Chrome browser session passed straight through without a visible interstitial. This is a
  stronger anti-bot posture than the block-page pattern already handled for Cinepolis/Texas
  Theatre/Angelika (`looks_blocked()`/`BLOCK_PAGE_MARKERS`), so `curl`/`httpx`/`curl_cffi`-only
  approaches are not viable here; a real browser context is required.

**Alternatives considered**:
- Plain HTTP fetch (`requests`/`httpx`/`curl_cffi`, per the project's `curl_cffi` precedent for
  Letterboxd) — rejected: confirmed live to hit the Queue-It/Cloudflare gate before reaching any
  showtime markup.
- Reverse-engineering a JSON API — rejected: none was observed on the wire during a live showtimes
  page load; the RSC payload itself is an internal Next.js serialization format, not a stable
  public contract, and is harder to parse reliably than the already-rendered DOM.

## §3. Rendered showtimes DOM shape

Confirmed live by loading the showtimes page in a real browser session:

- Content is grouped by **movie** (poster thumbnail, title, runtime, MPAA rating), e.g. "Moana",
  "The Odyssey".
- Each movie has one or more **format sections**, each with a header (e.g. `LASER AT AMC`, `IMAX
  WITH LASER AT AMC`) plus a row of attribute tags (`AMC Signature Recliners`, `Reserved Seating`,
  `Closed Caption`, `Audio Description`, `IMAX at AMC`, `AMC Artisan Films`, etc.) and a brand logo
  image (Cloudinary-hosted, e.g. `.../attributes/laser-at-amc.png`, `.../IMAX_with_Laser_at_AMC...`,
  `.../Dolby_SM.png`, `.../RealD_SM.png` — confirming Dolby Cinema and RealD 3D are both in use at
  this location in addition to standard/Laser/IMAX).
- Each format section has a row of clickable showtime buttons (e.g. `6:15pm`, `9:15pm`); near-capacity
  times carry an `ALMOST FULL` badge.
- A top nav bar exposes `AMC Stonebriar 24 ▾` (location), `Today ▾` (date), `All Movies ▾`, and
  `Premium Offerings ▾` filter controls.

**Decision**: Parse the format-section header text as the `format` field (e.g. `"LASER AT AMC"`,
`"IMAX WITH LASER AT AMC"`, `"Dolby Cinema"`, `"RealD 3D"`), matching how Texas Theatre's format
regex extraction and Angelika's `showtype.type` field are treated as opaque source-provided labels
rather than a fixed enum — consistent with spec FR-003's "when specified" wording.

## §4. Ticket URL

Clicking a showtime button (`6:15pm` for Moana) navigated to:

```
https://www.amctheatres.com/showtimes/145327763/seats
```

**Decision**: `ticket_url` is `https://www.amctheatres.com/showtimes/{session_id}/seats`.

**Confirmed at implementation time (tasks.md T003)**: each showtime button is a plain
`<a href="https://www.amctheatres.com/showtimes/{id}">{time text}</a>` anchor already present in
the rendered DOM — the numeric id is read directly from `href`, no click-through needed. The
anchor's own href has no `/seats` suffix; that suffix is appended by the app only once you actually
click through to the seat map (confirmed by following one link, read-only, no purchase/seat-select
action taken), so the scraper constructs `ticket_url` by appending `/seats` to the href itself.
Movie/format grouping (research.md §3) was also confirmed structurally at the same time: each film
is one `<section>` with an `<h1>` title, and one `<li aria-label="{Format Name} Showtimes">` per
format (e.g. `aria-label="IMAX with Laser at AMC Showtimes"`) — a more robust format signal than
parsing the `<h3>` tagline text, since the aria-label carries the format name alone with no
marketing tagline attached.

## §5. Date range / multi-day walk

**Confirmed at implementation time (tasks.md T003)**: the "Today ▾" control is a native
`<select name="date">`, already present in the initial page's server-rendered HTML (no extra
request needed to discover it) — 130 `<option>` elements were observed live, one per day of the
site's own published window, with the first option (`value=""`) meaning "today" and every other
option's `value` an ISO `YYYY-MM-DD` date. Passing that same value as a `?date=YYYY-MM-DD` query
string on the showtimes URL (confirmed by direct navigation) reloads the page already showing that
date's showtimes. The scraper therefore parses the initial page's own `<select name="date">` option
list as the authoritative full published window (mirroring how Angelika's date-strip was treated as
authoritative) and fetches one page per date via the query string — no guessed stop condition, no
per-day click-through, and no dependency on the earlier (incorrect) guess of a
`/showtimes/all/YYYY-MM-DD` path segment, which 500s.

## §6. Rating fallback (FR-008)

**Decision**: No new code required. TMDB-rating fallback when a source doesn't supply its own
movie rating is already a source-agnostic behavior in `enrich.py`/`storage.py` (restored in the
`f91ab02` commit, "Restore FR-007 compliance: fall back to TMDB rating..."), keyed by movie title
rather than per-cinema. AMC Stonebriar 24 showtimes automatically benefit once ingested, same as
every other source.

## §7. Non-film events

Unlike Texas Theatre, no non-film venue events (Q&As, rentals) were observed on the showtimes page
during this pass — every entry inspected was a standard theatrical release. AMC's showtimes page is
architecturally a dedicated showtimes browser (not a general events calendar like Texas Theatre's),
so no non-film classification/filtering logic is expected to be needed, consistent with Angelika's
`/films`-endpoint precedent (research.md §5 there) rather than Texas Theatre's calendar precedent.
A live run did surface one exception: a "Private Theatre Rental" listing renders as its own
"movie" section — excluded by title, not by a structured non-film flag (`NON_FILM_AMC_STONEBRIAR_TITLES`
in `scraper.py`).

## §8. Implementation-time findings (tasks.md T003, T021 live validation)

Two additional discoveries surfaced only once real code was run end-to-end against the live site —
recorded here since they materially changed the implementation from what §4/§5 originally proposed:

1. **The full ~130-day window is impractical to walk every run.** A live spot-check of a date 23
   days out (`?date=2026-08-15`) showed a full slate of 11 movies — AMC schedules its entire
   published window, not just the near term, unlike Angelika's ~2-week bookable strip or Texas
   Theatre's month-walk (which stops after two empty months and so rarely walks far in practice).
   Fetching all ~130 days would take several minutes per run, far past spec SC-004's 30-second
   target. **Decision**: cap the walk to `AMC_STONEBRIAR_MAX_WALK_DAYS = 14` days — a deliberate
   scope decision (documented in `scraper.py`), not a fetch failure, so a fully walked capped
   window still reports `complete=True`. A live run over the capped window captured 945 showtimes
   across all 14 days in ~30s wall time (including Python/browser startup).

2. **`wait_until="domcontentloaded"` alone raced the page's own client-side hydration.** The first
   live end-to-end run (uncapped) intermittently returned zero or wrong showtimes for several dates
   in the walk, inconsistently across repeated runs — `page.content()` was being captured before
   this Next.js page's own data/hydration had populated the showtimes `<section>` elements for that
   navigation. **Decision**: `_fetch_amc_stonebriar_page_with_retry` now calls
   `page.wait_for_selector("section, :text('No Showtimes')", timeout=timeout_ms)` after `goto()`
   and before `page.content()`, treating a selector timeout as "genuinely no showtimes that day"
   rather than a fetch error (bot-blocking is already ruled out earlier in the same function). This
   made the 14-day live run above fully deterministic (every day 2026-07-23 through 2026-08-05
   returned a populated, plausible showtime count).
