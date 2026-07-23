# Quickstart: Showtime Recommendation Rules

## Prerequisites

- Feature 001 (Cinepolis McKinney showtime ingestion) and feature 002
  (TMDB metadata enrichment) already deployed — this feature is not
  useful without a matched TMDB id per movie (spec FR-012)
- A public Letterboxd profile with a watchlist, if you want the watchlist
  criterion active (the profile must not be private)

## Configuration (new environment variables, both optional)

| Variable | Purpose | Example |
|---|---|---|
| `LETTERBOXD_USERNAME` | Source for the watchlist criterion | `daveyj` |
| `LETTERBOXD_RATING_THRESHOLD` | Minimum Letterboxd rating (0.5-5) for the rating criterion | `4.0` |

Per FR-005/SC-004, leaving both unset means **no showtime is ever marked
recommended** — this is intentional, not a bug. An invalid (non-numeric)
`LETTERBOXD_RATING_THRESHOLD` is treated the same as unset (FR-008), not
a startup error.

This is added alongside features 001/002's existing env vars — no new
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
  -e LETTERBOXD_USERNAME="<your-letterboxd-username>" \
  -e LETTERBOXD_RATING_THRESHOLD="4.0" \
  -e PUID=99 -e PGID=100 \
  -v /path/on/host/cinema-recs-data:/data \
  -p 8080:8080 \
  cinema-recs
```

## Validate it works

1. **Check recommendation logs** after a full ingestion/enrichment/
   recommendation cycle:
   ```bash
   docker logs -f cinema-recs
   ```
   Expect log lines showing the watchlist/best-of-list fetch outcome,
   and per-movie recommendation results with matched reason(s).

2. **View recommended showtimes** — open `http://<host>:8080/` and
   confirm showtimes for movies on your watchlist, above your rating
   threshold, or on the built-in best-of list are visually distinguished
   (badge/highlight) with their matched reason(s) shown (spec FR-006,
   FR-011, User Story 2).

3. **Confirm zero-config safety** — temporarily unset both
   `LETTERBOXD_USERNAME` and `LETTERBOXD_RATING_THRESHOLD`, restart, and
   confirm zero showtimes are marked recommended (spec SC-004).

4. **Confirm threshold changes take effect** — change
   `LETTERBOXD_RATING_THRESHOLD`, restart the container (no rebuild
   needed), and confirm previously-recommended showtimes that only
   matched via rating update accordingly on the next evaluation (spec
   User Story 3, SC-002).

5. **Confirm resilience to an unresolvable movie** — for a movie with no
   feature-002 TMDB match (or a match with no Letterboxd page), confirm
   it is never marked recommended and no error/broken row appears in the
   listing (spec FR-004, SC-003).

See [data-model.md](./data-model.md) for the schema and
[contracts/recommendation-interface.md](./contracts/recommendation-interface.md)
for the internal interface feature 004 will consume.
