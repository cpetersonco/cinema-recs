# Quickstart: Showtime Cancellation & Reschedule Alerts

## Prerequisites

- Feature 004 already deployed and delivering recommendation
  notifications — this feature has nothing to check for disappearance
  until at least one movie has been notified (spec: Dependencies)
- The same `DISCORD_WEBHOOK_URL` / `NOTIFICATIONS_ENABLED` configuration
  feature 004 uses; no new environment variables are introduced

## Configuration

None new. This feature reuses feature 004's `DISCORD_WEBHOOK_URL` and
`NOTIFICATIONS_ENABLED` as-is (spec FR-008) — see
[feature 004's quickstart](../004-showtime-notifications/quickstart.md#configuration-new-environment-variables-both-optional)
for those variables.

## Build and run

Same container, same run command as feature 004 — no new flags:

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

1. **Get a baseline recommendation notification** (feature 004): confirm
   a movie you expect to be recommended triggers a Discord message
   referencing a specific showtime, per feature 004's own quickstart.

2. **Simulate a cancellation** — once that showtime's Discord message has
   arrived, remove that specific showing from the source (or, for local
   testing, directly flip that `showtime` row's `status` to `stale` in
   the SQLite database and confirm the movie has no other active
   upcoming showtime), then trigger the next ingestion/notification
   cycle:
   ```bash
   docker logs -f cinema-recs
   ```
   Confirm a "cancelled" Discord message arrives referencing the movie
   title and the original date/time (spec FR-002, SC-001), and that it
   only arrives once even across further cycles (spec FR-004, SC-003).

3. **Simulate a reschedule** — repeat the above, but this time ensure the
   movie has another active upcoming showtime before the notified one
   disappears (e.g., a later showing already scraped, or ingest a new
   showing for the same movie in the same cycle the old one goes stale).
   Confirm a "rescheduled" Discord message arrives with both the original
   and new date/time (spec FR-003, SC-002).

4. **Confirm a rescheduled showing can later still be cancelled** — after
   step 3's reschedule alert, remove the new showing too (with no further
   replacement) and confirm a separate "cancelled" message follows on a
   later cycle (spec User Story 2 Acceptance Scenario 2).

5. **Confirm resilience to webhook failure** — temporarily point
   `DISCORD_WEBHOOK_URL` at an invalid/unreachable URL while a
   cancellation/reschedule would fire, confirm ingestion and
   recommendation evaluation still complete normally, the failure is
   logged, and the alert is delivered on a later cycle once the URL is
   fixed rather than being silently dropped (spec FR-007, SC-004).

6. **Confirm the disable switch covers this feature too** — set
   `NOTIFICATIONS_ENABLED=false`, restart, and confirm no
   cancellation/reschedule alerts are sent even when a previously-notified
   showing disappears (spec FR-008, SC-005).

See [data-model.md](./data-model.md) for the extended
`notification_record` schema and
[contracts/disappearance-alert-interface.md](./contracts/disappearance-alert-interface.md)
for the outbound webhook contract and feature 004 dependency.
