# Quickstart: Letterboxd Official Lists as Recommendation Filters

## Prerequisites

- Feature 003 (showtime recommendation rules) already deployed — this
  feature only extends its existing built-in best-of list mechanism, it
  doesn't stand alone.
- No new environment variables, volumes, or ports. This feature ships as
  a code-only change (data-model.md: `BUILT_IN_BEST_OF_LISTS` gains 8
  entries); nothing in `quickstart.md`'s `docker run` invocation changes
  from feature 003's.

## Build and run

```bash
docker build -t cinema-recs .

docker run -d \
  --name cinema-recs \
  -e CINEMA_RECS_SOURCE_URL="https://www.cinepolisusa.com/mckinney/showtimes" \
  -e CINEMA_RECS_REFRESH_INTERVAL_HOURS=3 \
  -e CINEMA_RECS_DATA_DIR=/data \
  -e CINEMA_RECS_PORT=8080 \
  -e TMDB_API_KEY="<your-tmdb-api-key>" \
  -e LETTERBOXD_USERNAME="<your-letterboxd-username>" \
  -e LETTERBOXD_RATING_THRESHOLD="4.0" \
  -e PUID=99 -e PGID=100 \
  -v /path/on/host/cinema-recs-data:/data \
  -p 8080:8080 \
  cinema-recs
```

## Validate it works

1. **Check refresh logs** after a full recommendation evaluation cycle:
   ```bash
   docker logs -f cinema-recs
   ```
   Expect one `Refreshed best-of list %r cache: %d film(s)` log line per
   onboarded list — 9 total (the existing `official_top_250` plus the 8
   new ones from data-model.md), each with a nonzero film count.

2. **Force a failure and confirm isolation** (User Story 2 / FR-003): if
   Letterboxd is briefly unreachable or one list's page 404s, the log
   line for that specific list becomes a `Failed to refresh Letterboxd
   best-of list %r` warning while the other 8 lists still log a normal
   success line in the same cycle — confirming one list's failure
   doesn't block or wipe the others.

3. **View recommended showtimes with list names** — open
   `http://<host>:8080/` and find a showtime whose movie you know ranks
   on one of the 8 new lists (e.g. a well-known horror film for "Top 250
   Horror Films"). Confirm the "Recommended (…)" text names the specific
   list by its real title (e.g. `Recommended (Top 250 Horror Films)`),
   not a raw key like `best_of:top_250_horror` (FR-004, User Story 1).

4. **Confirm multi-list matches list every match** — find or seed a
   showtime whose movie appears on more than one onboarded list (e.g.
   both "Letterboxd's Top 500 Films" and "Top 250 Horror Films") and
   confirm both names appear in the reasons text (User Story 1
   acceptance scenario 2), e.g.
   `Recommended (Letterboxd's Top 500 Films,Top 250 Horror Films)`.
