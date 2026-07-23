# Quickstart: Consolidated Movie Listings with Ticket and Letterboxd Links

## Prerequisites

- At least one source already onboarded and ingesting (features
  001/006/008) — this feature only changes how `GET /` presents already-
  ingested showtimes.
- Recommendation evaluation already running (feature 003) if you want to
  see the Letterboxd rating link populated — the rating/link come from
  `LetterboxdMovieData`, which `recommend.py`'s evaluation cycle
  populates, not from ingestion alone.
- No new environment variables.

## Build and run

Same container, same run command as prior features — no new flags:

```bash
docker build -t cinema-recs .

docker run -d \
  --name cinema-recs \
  -e CINEMA_RECS_SOURCE_URL="https://www.cinepolisusa.com/mckinney/showtimes" \
  -e CINEMA_RECS_REFRESH_INTERVAL_HOURS=3 \
  -e TMDB_API_KEY="<your-tmdb-api-key>" \
  -e LETTERBOXD_USERNAME="<your-letterboxd-username>" \
  -e LETTERBOXD_RATING_THRESHOLD="4.0" \
  -e DISCORD_WEBHOOK_URL="<your-discord-webhook-url>" \
  -e PUID=99 -e PGID=100 \
  -v /path/on/host/cinema-recs-data:/data \
  -p 8080:8080 \
  cinema-recs
```

## Validate it works

1. **Confirm consolidation** — ingest (or seed directly in SQLite) at
   least three active showtimes for the same movie at the same venue on
   different dates, then load `GET /`. Confirm exactly one row appears
   for that movie under that venue's section (spec User Story 1, SC-001)
   — not three.

2. **Confirm per-venue independence** — with a second cinema configured
   and the same movie also active there, confirm `GET /` shows one row
   for that movie under *each* venue's section (two rows total, not one
   merged row) — spec User Story 1, Acceptance Scenario 2.

3. **Confirm the ticket link** — for a movie whose representative
   (earliest active) showtime has a captured `ticket_url`, confirm the
   row shows a working link pointing to that same URL (spec User Story
   2, SC-002). For a movie whose representative showtime has no
   `ticket_url`, confirm the row shows "—" rather than a dead link (spec
   FR-004).

4. **Confirm the Letterboxd rating link** — after at least one
   recommendation evaluation cycle has run for a matched movie with a
   resolved Letterboxd rating, confirm its row's rating links to
   `https://letterboxd.com/film/<slug>/` and opens that movie's real
   Letterboxd page (spec User Story 3, SC-003). For a movie not yet
   enriched, or with no Letterboxd match, confirm the row shows "—"
   rather than an empty/broken link (spec FR-006).

5. **Confirm existing behavior is untouched** — verify "Recommended"
   highlighting, genre, and poster still display correctly on the
   (now single) row per movie (spec FR-007), and that `GET /health`
   still reports ingestion run outcomes exactly as before (spec FR-008).

See [contracts/web-view.md](./contracts/web-view.md) for the full updated
`GET /` response shape, and [data-model.md](./data-model.md) for which
existing data each column now draws from.
