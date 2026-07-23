# cinema-recs

Ingests movie showtimes for a cinema (currently: Cinepolis McKinney, the
"alpha" cinema for this pilot) and serves a minimal listing + ingestion
health view. Runs as a single Docker container, designed to be hosted on
an Unraid server.

Movie titles are also enriched with genre/overview/rating/poster data from
[TMDB](https://www.themoviedb.org/), cross-referenced against your
[Letterboxd](https://letterboxd.com/) watchlist, rating preferences, and a
built-in set of official Letterboxd best-of lists (Top 250, Top 500, and
genre/category lists like Horror, Animated, and Documentary) to flag
recommended showtimes, and — when a showtime
newly becomes recommended — announced via a Discord webhook. If that
notified showing is later cancelled or rescheduled by the cinema, a
follow-up Discord alert is sent too, reusing the same webhook
configuration (no separate setup required). See
[`specs/001-cinepolis-showtime-ingestion/`](specs/001-cinepolis-showtime-ingestion/),
[`specs/002-tmdb-metadata-enrichment/`](specs/002-tmdb-metadata-enrichment/),
[`specs/003-showtime-recommendation-rules/`](specs/003-showtime-recommendation-rules/),
[`specs/004-showtime-notifications/`](specs/004-showtime-notifications/),
[`specs/005-showtime-cancellation-alerts/`](specs/005-showtime-cancellation-alerts/),
[`specs/006-texas-theatre-source/`](specs/006-texas-theatre-source/),
and [`specs/007-unraid-cicd-autodeploy/`](specs/007-unraid-cicd-autodeploy/)
for the full specs, plans, and task breakdowns behind these features.

## Quickstart

Full setup, configuration, and validation steps live in
[`specs/001-cinepolis-showtime-ingestion/quickstart.md`](specs/001-cinepolis-showtime-ingestion/quickstart.md),
[`specs/002-tmdb-metadata-enrichment/quickstart.md`](specs/002-tmdb-metadata-enrichment/quickstart.md),
[`specs/003-showtime-recommendation-rules/quickstart.md`](specs/003-showtime-recommendation-rules/quickstart.md),
and [`specs/004-showtime-notifications/quickstart.md`](specs/004-showtime-notifications/quickstart.md).

Short version:

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
  -e NOTIFICATIONS_ENABLED="true" \
  -v ./data:/data \
  -p 8080:8080 \
  cinema-recs
```

`TMDB_API_KEY` is required — get a free API v3 key from your
[TMDB account's API settings](https://www.themoviedb.org/settings/api).
`LETTERBOXD_USERNAME` and `LETTERBOXD_RATING_THRESHOLD` are both
optional — leaving both unset means no showtime is ever marked
recommended (this is intentional, not a bug). `DISCORD_WEBHOOK_URL` is
also optional — leaving it unset means no notifications are ever sent;
`NOTIFICATIONS_ENABLED` (default `true` once a webhook URL is set) lets
you pause notifications without discarding the webhook URL.

Then visit `http://localhost:8080/` for the showtime listing and
`http://localhost:8080/health` for ingestion run status.

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install --with-deps chromium
export CINEMA_RECS_SOURCE_URL="https://www.cinepolisusa.com/mckinney/showtimes"
export TMDB_API_KEY="<your-tmdb-api-key>"
export LETTERBOXD_USERNAME="<your-letterboxd-username>"
export LETTERBOXD_RATING_THRESHOLD="4.0"
export DISCORD_WEBHOOK_URL="<your-discord-webhook-url>"
export PYTHONPATH=src
python -m pytest
python main.py ingest-once
```

Letterboxd scraping uses `curl_cffi` (TLS/browser-fingerprint impersonation)
rather than plain `requests`, since anonymous plain-`requests` traffic to
`letterboxd.com` is liable to trip Cloudflare's rate limiting under any
real request volume — this was hit and confirmed during development.

## Deployment (CI/CD)

Every push to `main` runs `.github/workflows/deploy.yml`: `pytest`
(hard gate — a failing commit is never built or published), `ruff`
(advisory only, since this repo has pre-existing style findings that
predate this pipeline), then a `linux/amd64` image build tagged both
`latest` and the commit's short SHA, published to
`ghcr.io/cpetersonco/cinema-recs` using the workflow's built-in
`GITHUB_TOKEN` (no manually-created secret needed).

On Tower, a single host-wide [Watchtower](https://containrrr.dev/watchtower/)
instance (installed once via Unraid's Community Applications store, not
part of this repo) polls that image and automatically recreates the
`cinema-recs` container when a new one is published, preserving the
`/data` volume. It's scoped to this container only via the
`com.centurylinklabs.watchtower.enable: "true"` label already set in
`docker-compose.yml`, so it won't touch unrelated containers on the
host. The currently running commit is shown on `/health` under
"Running version".

One-time setup steps (GitHub Actions permissions, making the GHCR
package public, installing/configuring Watchtower on Tower) are in
[`specs/007-unraid-cicd-autodeploy/quickstart.md`](specs/007-unraid-cicd-autodeploy/quickstart.md).

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
