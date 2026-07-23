# Quickstart: Cinepolis McKinney Showtime Ingestion

## Prerequisites

- Docker installed (locally, or on the target Unraid host)
- Network access to Cinepolis' website from wherever the container runs

## Configuration (environment variables)

| Variable | Purpose | Example |
|---|---|---|
| `CINEMA_RECS_SOURCE_URL` | Cinepolis McKinney showtimes page (used to establish a Cloudflare-cleared session before calling the site's GraphQL API) | `https://www.cinepolisusa.com/mckinney/showtimes` |
| `CINEMA_RECS_REFRESH_INTERVAL_HOURS` | How often ingestion re-runs | `3` |
| `CINEMA_RECS_DATA_DIR` | Directory for the SQLite database file (mount as a volume) | `/data` |
| `CINEMA_RECS_PORT` | Port the web view listens on | `8080` |
| `PUID` | UID the container process runs as (owns files under the data dir) | `99` |
| `PGID` | GID the container process runs as | `100` |

## Build and run

```bash
docker build -t cinema-recs .

docker run -d \
  --name cinema-recs \
  -e CINEMA_RECS_SOURCE_URL="https://www.cinepolisusa.com/mckinney/showtimes" \
  -e CINEMA_RECS_REFRESH_INTERVAL_HOURS=3 \
  -e CINEMA_RECS_DATA_DIR=/data \
  -e CINEMA_RECS_PORT=8080 \
  -e PUID=99 \
  -e PGID=100 \
  -v /path/on/host/cinema-recs-data:/data \
  -p 8080:8080 \
  cinema-recs
```

`PUID`/`PGID` default to Unraid's conventional `nobody`/`users` values
(`99`/`100`) so the container doesn't assume a specific host UID/GID; the
entrypoint `chown`s the data directory to match before dropping to that
user.

On Unraid, the same environment variables and the `/data` volume mapping
translate directly into the Unraid Docker UI's variable/path fields.

## Validate it works

1. **Check startup logs** for the first ingestion run outcome:
   ```bash
   docker logs -f cinema-recs
   ```
   Expect a log line indicating success/failure and a showtime count
   (spec FR-009).

2. **View ingested showtimes** — open `http://<host>:8080/` and confirm
   movie titles, dates, start times, and formats are listed and match
   what Cinepolis' own site currently shows for the McKinney location
   (spec SC-001, SC-006).

3. **Check ingestion health** — open `http://<host>:8080/health` and
   confirm the most recent run's outcome and showtime count are visible
   (spec SC-004). Temporarily point `CINEMA_RECS_SOURCE_URL` at an
   unreachable address and restart to confirm a `failure` outcome is
   visibly distinct from a zero-showtime success.

4. **Re-run ingestion without source changes** (wait for the next
   scheduled run, or restart the container) and confirm the showtime
   count and listing are unchanged — no duplicates appear (spec SC-002).

5. **Confirm ticket URLs are captured** (spec FR-011) — query the
   `showtime` table directly (or check logs) and confirm `ticket_url` is
   populated as `https://www.cinepolisusa.com/mckinney/checkout/seats/{id}`
   for active showtimes; open one in a browser and confirm it lands on
   that showing's real seat-selection page.

See [data-model.md](./data-model.md) for the underlying schema and
[contracts/web-view.md](./contracts/web-view.md) for the exact view
behavior being validated.
