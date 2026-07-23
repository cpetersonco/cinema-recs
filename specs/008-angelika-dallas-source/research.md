# Research: Angelika Film Center Dallas Showtime Ingestion Source

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## 1. Site Platform & Fetch/Parse Method

### Decision
Fetch showtimes from Reading Cinemas' JSON API at `production-api.readingcinemas.com` (via Playwright, matching the Cinepolis precedent), not by scraping server-rendered HTML.

### Rationale
- `curl`ing `https://angelikafilmcenter.com/dallas` returns a ~6KB single-page-app shell (`<div id="root"></div>`, `main.4a19fcb4.js`) with no server-rendered showtime markup — this is a React SPA, not a static/WordPress-style page like Texas Theatre.
- The page's own bundled JS (`main.4a19fcb4.js`) references `production-api.readingcinemas.com` and route fragments including `/movies`, `/movies/details/:cinemaId/:movieGroupId`, `/sessions/`, and `/cinemas/:cinemaId/sessions/:sessionId/:movieId` — confirming showtimes are loaded client-side from this API, keyed by a per-venue `cinemaId`.
- Angelika Film Center is operated by Reading International; the same JS bundle and API host also serve `readingcinemas.com` and `consolidatedtheatres.com` (selected at runtime via `window.location.href`), so this is a shared multi-brand booking platform, not an Angelika-specific system.
- This mirrors the existing Cinepolis integration (`scraper.py`): a Vue/Quasar SPA backed by a GraphQL API discovered via live network inspection rather than static HTML parsing.

### Alternatives Considered
- **Static HTML parsing (BeautifulSoup, as used for Texas Theatre)**: Not viable — the served HTML contains no showtime data at all; it is populated entirely by client-side JS after the initial page load.
- **Playwright `page.content()` after JS render (DOM scraping) instead of hitting the API directly**: Would work but is slower and more brittle than calling the JSON API directly, since it requires waiting for React hydration and depends on CSS class names that can change with frontend deploys, whereas the API response shape is more stable. Following the Cinepolis precedent, prefer sniffing/replaying the API request over DOM scraping.

### Confirmed via Live Network Inspection (2026-07-22)
Live browser inspection of `https://angelikafilmcenter.com/dallas` (network capture + in-page
`JSON.parse`/`fetch` hooking) confirmed the following:

- **Endpoint**: `GET https://production-api.readingcinemas.com/films`
- **Query params**: `countryId=6`, `cinemaId=0000000009` (Dallas venue), `status=getShows`,
  `flag=initial`, `selectedDate=` (empty string fetches the full upcoming schedule in one call;
  the UI's per-day tabs filter this client-side rather than issuing a new request per day).
- **Auth/CORS**: The endpoint is protected by an AWS-style WAF/CORS policy that rejects a bare
  `fetch()`/`curl` call from an arbitrary script or shell (`{"message":"Forbidden"}` / opaque
  CORS failure), even with a plausible-looking per-brand key extracted from the JS bundle
  (`LdqxbzWVjYST0YVmuKdkXA8yPQye4JobVoX6sRtWajA` for the `AFC` brand) — the exact signing/header
  scheme was not recovered. **Decision**: rather than replaying a hand-crafted request (the
  Cinepolis approach), the scraper MUST let the real page load normally and capture the
  **response** to its own authenticated request via Playwright's `page.on("response")` /
  `page.expect_response()` (matching on `"/films"` in the URL and `cinemaId=0000000009` in the
  query string), then call `.json()` on that response. This is simpler and more robust than
  Cinepolis' header-replication approach and requires no knowledge of the auth scheme at all,
  since Playwright's network layer observes the response regardless of page-script CORS
  restrictions.
- **Response shape** (`nowShowing.data.movies[]`, one entry per film):
  ```json
  {
    "nowShowing": {
      "statusCode": 0,
      "data": {
        "movies": [
          {
            "name": "THE ODYSSEY IN 70MM",
            "slug": "2523",
            "movieSlug": "the-odyssey-in-70mm",
            "ratingName": "",
            "length": "...",
            "showdates": [
              {
                "date": "2026-07-23",
                "showtypes": [
                  {
                    "type": "70mm",
                    "subType": "",
                    "amenities": ["70mm"],
                    "showtimes": [
                      {
                        "id": "94651",
                        "ScheduledFilmId": "HO00008448",
                        "date_time": "2026-07-23T09:00:00-05",
                        "auditorium": "",
                        "availableSeats": "282",
                        "enabled": true,
                        "type": "70mm",
                        "soldout": false
                      }
                    ]
                  }
                ]
              }
            ]
          }
        ],
        "filter": {}
      }
    }
  }
  ```
- **Format field**: `showtypes[].type` (e.g. `"70mm"`, presumably `"standard"`/`"3d"` etc. for
  other listings) is already a clean, structured format label — no title-text regex extraction
  is needed (unlike Texas Theatre). This directly satisfies FR-003/US2 with no fallback logic
  required.
- **DateTime**: `showtimes[].date_time` is an ISO 8601 timestamp with a local UTC offset (e.g.
  `-05` for CDT) already applied — no separate `CENTRAL_TIME` conversion is needed, only ISO
  parsing. Note: Python's `datetime.fromisoformat()` (3.11) does not accept a bare `-05` offset
  (no minutes component); the implementation must normalize it to `-05:00` before parsing (regex:
  append `:00` when the string ends in exactly `[+-]\d{2}`).
- **Ticket/detail URL**: No explicit ticket URL field is returned. The JS bundle's router
  contains the route pattern `/cinemas/:cinemaId/sessions/:sessionId/:movieId`; combined with the
  confirmed `cinemaId` (`0000000009`), each showtime's own `id` (session id, e.g. `"94651"`), and
  the movie's `slug` (numeric movie id, e.g. `"2523"`), the ticket URL is constructed as
  `https://angelikafilmcenter.com/cinemas/0000000009/sessions/{session_id}/{movie_slug}`
  — same reasoning as the Cinepolis `TICKET_URL_TEMPLATE` (confirmed by the site's own router,
  not by completing a live purchase flow).
- **Non-film events**: This `/films` endpoint returns only films — Angelika Dallas's site has no
  separate non-film-event feed mixed into it (unlike Texas Theatre's single calendar). FR-008 is
  satisfied trivially: no classification/filtering logic is needed for this source.

---

## 2. Presentation Format Extraction

### Decision (Confirmed)
Use `showtypes[].type` directly from the `/films` response as the `format` value (e.g. `"70mm"`)
— it is already a clean, structured label. No regex/title parsing is needed.

### Rationale
- Confirmed via live inspection (section 1): each `showdates[].showtypes[]` entry carries its own
  `type` string, and every `showtimes[]` entry under it also repeats the same `type` — a
  discrete, structured field, not embedded in freeform text.

### Alternatives Considered
- **Regex-based title parsing (Texas Theatre style)**: Not needed — rejected now that the
  structured field is confirmed present and reliable.

---

## 3. Timezone & DateTime Handling

### Decision (Confirmed)
Parse `showtimes[].date_time` (e.g. `"2026-07-23T09:00:00-05"`) directly with
`datetime.fromisoformat()` after normalizing the offset to include a minutes component
(`-05` → `-05:00`); no separate timezone conversion is needed since the API already returns
locally-offset wall-clock time. `CENTRAL_TIME`/`ZoneInfo("America/Chicago")` is not required for
this source (kept only as a cross-check/assumption reference, since Dallas is in Central Time).

### Rationale
- Confirmed via live inspection: the API's own timestamps carry the correct local UTC offset
  already, unlike Cinepolis (which returns bare UTC and requires `.astimezone(CENTRAL_TIME)`).

---

## 4. Deduplication & Idempotency

### Decision
Identify unique showtimes using the same tuple `(cinema_id, movie_title, show_date, start_time)` used by every existing source, and reuse `storage.upsert_showtime` / `storage.mark_stale_showtimes` unchanged.

### Rationale
- This is the established, shared dedup contract across all sources (Cinepolis, Texas Theatre) — no new behavior is required; the new source only needs to produce `ScrapedShowtime` records in the existing shape for the existing storage layer to handle correctly.

---

## 5. Non-Film Event Filtering

### Decision (Confirmed)
No filtering logic is needed. The `/films` endpoint returns only films (`nowShowing.data.movies[]`)
— there is no mixed non-film-event feed to exclude from, unlike Texas Theatre's single calendar
that lists concerts/comedy/live music alongside screenings.

### Rationale
- Confirmed via live inspection: Reading Cinemas' booking platform separates content types by
  endpoint/section; the showtimes API this feature consumes is films-only by construction.
