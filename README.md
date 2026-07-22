# cinema-recs

Ingests movie showtimes for a cinema (currently: Cinepolis McKinney, the
"alpha" cinema for this pilot) and serves a minimal listing + ingestion
health view. Runs as a single Docker container, designed to be hosted on
an Unraid server.

See [`specs/001-cinepolis-showtime-ingestion/`](specs/001-cinepolis-showtime-ingestion/)
for the full spec, plan, and task breakdown behind this feature.

## Quickstart

Full setup, configuration, and validation steps live in
[`specs/001-cinepolis-showtime-ingestion/quickstart.md`](specs/001-cinepolis-showtime-ingestion/quickstart.md).

Short version:

```bash
docker build -t cinema-recs .
docker run -d \
  --name cinema-recs \
  -e CINEMA_RECS_SOURCE_URL="https://www.cinepolisusa.com/mckinney/showtimes" \
  -e CINEMA_RECS_REFRESH_INTERVAL_HOURS=3 \
  -v ./data:/data \
  -p 8080:8080 \
  cinema-recs
```

Then visit `http://localhost:8080/` for the showtime listing and
`http://localhost:8080/health` for ingestion run status.

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install --with-deps chromium
export CINEMA_RECS_SOURCE_URL="https://www.cinepolisusa.com/mckinney/showtimes"
export PYTHONPATH=src
python -m pytest
python main.py ingest-once
```

## How showtime fetching works

Cinepolis' site is behind Cloudflare bot protection (blocks plain HTTP
requests and even default headless Chromium) and is a client-rendered
Vue/Quasar SPA with no showtime markup in its HTML. `scraper.py` instead:
loads the McKinney showtimes page with a stealth-enabled headless browser
(clears Cloudflare), then calls Cinepolis' own `/graphql` API from inside
that page's JS context (a separate HTTP client gets blocked even with
valid session cookies — only an in-page `fetch()` works). See
`specs/001-cinepolis-showtime-ingestion/research.md` for the full
investigation.

**Known limitation**: the API's `showingsForDate` query doesn't return a
human-readable format/auditorium label (e.g. "4DX"/"VIP") — only a
`screenId`. `format` is currently always `None`; resolving it would need
a separate screens lookup not yet implemented. This is an undocumented
internal API, so it could change without notice.
