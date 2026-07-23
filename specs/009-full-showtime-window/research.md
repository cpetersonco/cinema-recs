# Research: Full Showtime Window Ingestion

## 1. Cinepolis (McKinney) — GraphQL, one date per query

**Current behavior**: `scrape_showtimes(source_url, show_date=None)` calls
`fetch_showings_json(source_url, show_date)` once, for a single date
(defaults to today). `fetch_showings_json` launches a *new* Playwright
Chromium browser, navigates to the SPA once (to pass Cloudflare), then
runs one `page.evaluate` GraphQL `fetch()` for that single date.

**Decision**: Loop over consecutive dates starting today, reusing the
*same* browser/page across all dates in one run (navigate once, then run
one `page.evaluate` per date against the already-authorized page), rather
than relaunching a browser per date. Stop once a configurable number of
consecutive dates (2) report `count == 0`, to tolerate a single
legitimately empty day (e.g. a Monday dark day) without treating it as
"reached the end of the published calendar."

**Rationale**: The GraphQL endpoint has no "give me everything" query —
per-date is the only shape available (confirmed by the existing query in
`scraper.py`). Relaunching a full Chromium browser per date (as the
current per-attempt retry structure does) would multiply run time and
Cloudflare-challenge risk by the number of dates fetched; reusing one
already-trusted page's JS context for N `fetch()` calls avoids that while
preserving the "must originate from the loaded page" requirement that
makes the Cloudflare bypass work at all.

**Alternatives considered**:
- Launch a new browser per date (simplest, reuses existing
  `fetch_showings_json` unchanged in a loop) — rejected: multiplies
  Cloudflare-challenge exposure and run time roughly linearly with the
  number of dates in the horizon, working against Story 3's reliability
  goal.
- Query a wide date range in one GraphQL call — rejected: the API schema
  (probed directly, introspection disabled) only exposes
  `showingsForDate(date, siteIds)`; no range/list parameter exists to
  request.

## 2. Texas Theatre — server-rendered calendar, one month per page

**Current behavior**: `scrape_texas_theatre_showtimes(source_url)`
fetches exactly one calendar page (default `/calendar`, meaning "the
current month").

**Live verification** (fetched during planning, 2026-07-23):
`https://thetexastheatre.com/calendar` links to `/calendar/august/2026`
(and back to `/calendar/july/2026`); every subsequent month page carries
its own prev/next month links, and the site happily generates pages for
months with zero listings (verified through `/calendar/february/2027`,
which returns 0 `calendar-listing` blocks). Listing counts observed while
walking forward from the current month: Jul 23 / Aug 38 / Sep 4 / Oct 5 /
Nov 2 / Dec 1 / Jan 0 / Feb 0 — i.e. counts taper unevenly and do **not**
monotonically decrease before hitting zero (Sep < Oct here), so a single
zero month is not a safe stop condition on its own.

**Decision**: Starting from the current month, follow the page's own
"next month" link forward, accumulating listings, until 2 consecutive
months each return 0 listings — then treat the month before that streak
as the end of the published calendar.

**Rationale**: The site's own navigation (not a guessed URL scheme) is
authoritative for "next month," so following it is more robust than
constructing `/calendar/<month>/<year>` URLs by hand. The empirically
observed non-monotonic tapering (Sep=4 < Oct=5) rules out stopping on the
first zero month; requiring 2 consecutive zeros balances not stopping
early against not walking arbitrarily far into a calendar the site will
generate forever.

**Alternatives considered**:
- Stop on the first zero-listing month — rejected: would have
  incorrectly truncated the calendar between Sep (4) and Oct (5) had Sep
  been zero instead of 4, per the observed non-monotonic pattern.
- Fetch a fixed number of months (e.g. always 6) regardless of content —
  rejected: violates FR-006 (no artificial cutoff); would either
  over-fetch known-empty months or under-fetch if the source ever
  publishes further out than today's observed horizon.

## 3. Angelika Dallas — per-date `/films` API, walked via its own date-selector strip

**Superseded finding**: Planning-time analysis originally guessed the
`/films` response's `nowShowing.data.movies[].showdates[]` array was
already multi-date per call, since the field is a plural array. **Live
verification during implementation (2026-07-23) disproved this**: a real
capture showed `nowShowing` only ever contains a single date's data per
response, and the captured request URL always carries a `selectedDate`
query parameter (empty on initial load, meaning "today" implicitly) —
`https://production-api.readingcinemas.com/films?...&selectedDate=`.
This source is date-scoped exactly like Cinepolis, not full-window.

**Live verification of the fetch mechanism**: A hand-crafted
cross-origin `fetch()` to `production-api.readingcinemas.com` from
within the loaded page still fails (`TypeError: Failed to fetch`,
confirming the existing WAF/CORS comment). However, the "now playing"
page (`/dallas` and `/dallas/now-playing`, both work) renders its own
date-selector strip (`div#anytime > span`, one button per selectable
date, e.g. `"Today, 7/23"`, `"Tomorrow, 7/24"`, `"Sunday 7/26"`, ...
`"Wednesday 1/13"`). Clicking one of those buttons makes the site's own
frontend re-issue the `/films` request with that date's `selectedDate`
filled in (confirmed live: clicking "Sunday 7/26" produced a request
ending `...&selectedDate=2026-07-26`, whose response's only `showdates`
entry was `2026-07-26`). The strip itself already enumerates every date
the source currently has real showtimes for — a full live run captured
76 distinct dates from 2026-07-23 through 2027-01-12 (~6 months), 858
showtimes, completing in ~65s.

**Decision**: Walk the date-selector strip exactly as declared, not a
heuristic stop condition:
1. On initial page load, capture the `/films` response as before (this
   already covers the strip's first date, "today" — no extra request
   needed for it).
2. Read every `div#anytime > span` label from the loaded DOM
   (`_extract_angelika_labeled_dates`), parsing each `"Weekday M/D"` /
   `"Today, M/D"` / `"Tomorrow, M/D"` label into a real date (rolling
   over to next year when the parsed month/day is earlier than today —
   the strip only ever runs forward).
3. For every remaining labeled date, click its button and capture the
   resulting `/films` response (`_click_angelika_date_with_retry`,
   retried per-date like the other sources), reusing one browser/page
   for the whole run.
4. `complete=True` once every labeled date has been fetched; `False` if
   a date's click+capture exhausts its retries partway through.

This directly satisfies FR-002/FR-006: the stop condition is not a
guessed "N empty periods" heuristic (as needed for Cinepolis/Texas
Theatre, which expose no equivalent authoritative list) but the source's
own already-computed enumeration of its full booking horizon for
currently-open movies.

**Rationale**: Reading the strip's declared list once, rather than
probing forward speculatively, avoids an open-ended walk — the label
list is finite and known immediately after the first page load, so the
walk has a hard, source-declared end from the start rather than
"probably far enough." It also proved necessary in practice: showtimes
were still present as late as December 25 in the live capture, so a
consecutive-empty-dates heuristic (as used for Cinepolis) would not have
terminated early and offers no advantage here.

**Alternatives considered**:
- Trust the originally-guessed multi-date response shape — rejected once
  live capture disproved it; kept in this document only as the corrected
  record of what was actually found.
- Reverse-engineer the WAF/CORS-gated API to call it directly with
  `selectedDate` — rejected: the existing module-level comment already
  documents this was tried and rejected for the initial-load case;
  clicking the site's own UI and capturing its own authenticated request
  (as the original single-date design already did) is the lower-risk,
  already-proven mechanism, just applied per date instead of once.
- Advance-tickets endpoint (`advanceTicket.data.advSessions`, covering
  not-yet-open/upcoming releases) — inspected live but rejected for this
  source's showtime data: it only reports aggregate showtime *counts*
  per date/type (e.g. `{"showtimes": 5, "type": "Standard"}`), not
  individual session `id`/`date_time` fields needed to build
  `ScrapedShowtime` records or ticket URLs. Out of scope for this
  feature (coming-soon/advance-ticket movies aren't currently modeled by
  this app at all); left for a future feature if ever needed.

## 4. Stale-marking safety across a multi-request fetch (FR-003, FR-004)

**Current behavior**: `run_ingestion` calls `storage.mark_stale_showtimes`
unconditionally after any non-exception scrape result, including when
zero showtimes come back or some entries were skipped during parsing
("partial" outcome) — i.e. today, a scraper's *return value* is trusted
even if it silently under-fetched.

**Decision**: Introduce a per-source "fetch completed the full window"
signal (e.g. the scrape result records whether the date/month walk
finished by legitimately reaching its stop condition vs. exiting early
due to a fetch failure part way through). `run_ingestion` MUST only call
`mark_stale_showtimes` when that signal is true; when a multi-step fetch
fails partway through, the run is recorded as `failure` (or `partial`,
reusing the existing outcome field) using whatever showtimes were
successfully captured before the failure for `showtimes_captured`, but
without ever calling `mark_stale_showtimes` for that run.

**Rationale**: This is the mechanism that directly satisfies FR-003/
FR-004/SC-003 — the existing "partial" outcome already distinguishes
"reachable but some entries dropped during parsing" from "success"; this
extends that same distinction to "reachable but the full-window walk
didn't finish," which is a new failure mode introduced specifically by
fetching more than one page/date per run.

**Alternatives considered**:
- Keep calling `mark_stale_showtimes` on any non-exception result
  (today's behavior) — rejected: this is precisely the bug the feature
  exists to fix; a scraper that raises partway through a 6-month walk
  would otherwise still report whatever partial list it collected as if
  it were complete.

## 5. Request pacing across a larger number of fetches

**Decision**: Keep the existing `MAX_FETCH_ATTEMPTS`/`RETRY_BACKOFF_SECONDS`
retry model per unit of work (date for Cinepolis, month for Texas
Theatre), and rely on Cloudflare/WAF bypass already established once per
run (single browser context reused across dates/months) rather than
adding new rate-limiting logic.

**Rationale**: Constitution IV (Simplicity) — no evidence yet that either
site's bot protection is sensitive to *volume* of same-session requests
(only to lacking a real browser fingerprint at all, which reusing one
authorized page/context already satisfies). Add explicit inter-request
delays only if implementation-time testing against the live sites shows
throttling; not assumed speculatively here.

**Alternatives considered**:
- Add a fixed delay between every date/month request up front —
  rejected as premature; no evidence of a rate-limit problem, and it
  would slow down every ingestion run for a risk that hasn't been
  observed.
