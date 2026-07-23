# Quickstart: Showtime Notifications

## Prerequisites

- Features 001-003 already deployed, with feature 003 actually
  configured (a `LETTERBOXD_USERNAME` and/or `LETTERBOXD_RATING_THRESHOLD`)
  — with no feature-003 preferences active, nothing is ever recommended,
  so this feature has nothing to notify about (spec FR-007)
- A Discord webhook URL (Discord server → channel settings → Integrations
  → Webhooks → New Webhook → Copy Webhook URL)

## Configuration (new environment variables, both optional)

| Variable | Purpose | Example |
|---|---|---|
| `DISCORD_WEBHOOK_URL` | Destination for notifications | `https://discord.com/api/webhooks/...` |
| `NOTIFICATIONS_ENABLED` | Explicit on/off switch (default `true`) | `false` |

Leaving `DISCORD_WEBHOOK_URL` unset means notifications never fire (spec
FR-007), same as feature 003's zero-config safety default.

## Build and run

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

1. **Check notification logs** after a full ingestion/enrichment/
   recommendation/notification cycle:
   ```bash
   docker logs -f cinema-recs
   ```
   Expect log lines showing notification attempts per newly-recommended
   movie, with outcome (`sent`/`failed`).

2. **Confirm a real Discord message** — for a movie you expect to be
   recommended (on your watchlist, above your rating threshold, or on the
   built-in best-of list), confirm a message arrives in the configured
   Discord channel containing the movie title, its next showtime's date/
   time, the matched reason(s) (spec FR-002, SC-001), and a working
   ticket-purchase link when feature 001 captured one for that showtime
   (spec FR-002a) — click it and confirm it lands on the real
   seat-selection page.

3. **Confirm no duplicate notifications** — let a second
   ingestion/evaluation cycle run (or trigger one manually) while the
   same movie remains recommended, and confirm no second message is sent
   for it (spec FR-003, SC-002).

4. **Confirm resilience to webhook failure** — temporarily point
   `DISCORD_WEBHOOK_URL` at an invalid/unreachable URL, trigger
   evaluation, and confirm ingestion/recommendation evaluation still
   complete normally, the failure is logged, and (once the URL is fixed)
   the same movie is notified on the next cycle rather than being
   silently skipped forever (spec FR-005, SC-003).

5. **Confirm the disable switch** — set `NOTIFICATIONS_ENABLED=false`,
   restart, and confirm no notifications are sent even for movies that
   are newly recommended (spec FR-006/FR-007, SC-004).

See [data-model.md](./data-model.md) for the schema and
[contracts/notification-interface.md](./contracts/notification-interface.md)
for the outbound webhook contract and feature 003 dependency.
