# Quickstart: Movie Metadata Enrichment via TMDB

## Prerequisites

- Feature 001 (Cinepolis McKinney showtime ingestion) already deployed
  and ingesting real showtimes
- A TMDB API key ([themoviedb.org](https://www.themoviedb.org/) account
  → API settings) — free to obtain

## Configuration (new environment variable)

| Variable | Purpose | Example |
|---|---|---|
| `TMDB_API_KEY` | TMDB API v3 key used for all enrichment lookups | `abc123...` |

This is added alongside feature 001's existing env vars
(`CINEMA_RECS_SOURCE_URL`, `CINEMA_RECS_REFRESH_INTERVAL_HOURS`,
`CINEMA_RECS_DATA_DIR`, `CINEMA_RECS_PORT`, `PUID`, `PGID`) — no new
volume or port is required.

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
  -e PUID=99 -e PGID=100 \
  -v /path/on/host/cinema-recs-data:/data \
  -p 8080:8080 \
  cinema-recs
```

## Validate it works

1. **Check enrichment logs** after an ingestion cycle:
   ```bash
   docker logs -f cinema-recs
   ```
   Expect log lines showing enrichment attempts per newly ingested movie
   title, with outcome (`matched`/`unmatched`/`failed`) and, for
   matches, the TMDB identifier stored (spec FR-008).

2. **View enriched showtimes** — open `http://<host>:8080/` and confirm
   genre, rating, and poster now appear alongside movie title/date/time/
   format for matched movies, while unmatched movies still display
   normally without a broken section (spec SC-004, User Story 3).

3. **Confirm caching** — re-run ingestion/enrichment without new movies
   appearing, and confirm (via logs or a quick DB query) that no repeat
   TMDB lookups occur for already-enriched titles (spec SC-002).

4. **Confirm ingestion resilience** — temporarily set `TMDB_API_KEY` to
   an invalid value (or block network access to TMDB) and confirm
   showtime ingestion itself still completes normally; only enrichment
   attempts fail and are logged (spec SC-003).

5. **Spot-check accuracy** — for a handful of matched movies, confirm
   the displayed genre/rating/poster actually correspond to that movie
   (not a different film with a similar title) — this is the manual
   check behind SC-005 (zero mismatched-metadata incidents).

See [data-model.md](./data-model.md) for the schema and
[contracts/movie-metadata-interface.md](./contracts/movie-metadata-interface.md)
for the internal interface feature 003 will consume.
