# Research: Texas Theatre Showtime Source Ingestion

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## 1. Calendar Page Source & Parsing Method

### Decision
Use Playwright-based HTML scraping (leveraging the existing `src/cinema_recs/scraper.py` pattern and stealth browser context) to fetch and parse `https://thetexastheatre.com/calendar`.

### Rationale
- The existing codebase standardizes on Playwright (`playwright.sync_api` with `Stealth` plugin) for website fetching to handle bot-protection headers, dynamic JS rendering, and modern browser navigation.
- HTML structure on the Texas Theatre calendar includes event cards with titles, dates, screening times, detail/ticket URLs, and projection format notes (e.g., 35mm, 70mm).
- Using Playwright ensures consistent error handling, Cloudflare block detection (`BLOCK_PAGE_MARKERS`), and retry backoff already established in `cinema-recs`.

### Alternatives Considered
- **Direct HTTP Requests (requests/httpx) + BeautifulSoup**: Faster runtime execution, but vulnerable to site layout changes, JavaScript-rendered event listings, or Cloudflare bot challenges without realistic user agent / browser TLS fingerprints.
- **Third-Party Movie API (e.g. Fandango/Gracenote)**: Independent theaters like Texas Theatre often do not publish full rep house schedules to national aggregators, making direct calendar ingestion necessary for accurate rep showtimes.

---

## 2. Projection Format Extraction Logic

### Decision
Extract presentation format strings from event titles, subtitled event metadata, and event descriptions using pattern matching for common film formats: `35mm`, `70mm`, `16mm`, `4K`, `DCP`, `Digital`.

### Rationale
- Texas Theatre specializes in archival film prints (35mm and 70mm screenings).
- Titles or descriptions frequently contain explicit format tags such as `"THE SHINING - 35mm"` or `"2001: A SPACE ODYSSEY [70mm]"` or `"In 35mm!"`.
- Normalizing these into standard values (e.g., `35mm`, `70mm`, `16mm`, `Digital`) populates `Showtime.format` accurately without breaking schema constraints.

### Alternatives Considered
- **Defaulting format to NULL or "Digital"**: Omits critical value for users specifically looking for analog 35mm/70mm film projections.
- **Unstructured raw format strings**: Creates messy tags in recommendations; regularized format strings make filtering simple.

---

## 3. Timezone & DateTime Handling

### Decision
Parse all calendar event dates and start times in Central Time (`America/Chicago` / `ZoneInfo("America/Chicago")`). Convert start times to `datetime.date` and `datetime.time` objects for storage.

### Rationale
- Texas Theatre is located in Dallas, TX (Central Time).
- The calendar publishes local wall-clock showtimes (e.g., "7:30 PM", "9:45 PM").
- Central Time matches the existing `CENTRAL_TIME` timezone configured in `scraper.py`.

---

## 4. Deduplication & Idempotency

### Decision
Identify unique showtimes using the tuple `(cinema_id, movie_title, show_date, start_time)`. Re-ingestions will upsert existing records and update `last_seen_at` and `status = 'active'`, while un-seen records will be marked `status = 'stale'` via existing `storage.mark_stale_showtimes`.

### Rationale
- Matches existing showtime storage logic in `storage.py` and `ingest.py`.
- Guarantees zero duplicate records on repeated ingestion runs.
