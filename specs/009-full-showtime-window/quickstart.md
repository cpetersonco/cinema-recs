# Quickstart: Full Showtime Window Ingestion

## Prerequisites

- Features 001/006/008 (the three source scrapers) and feature 005
  (cancellation/reschedule alerts) already deployed — this feature
  changes how much of each source's calendar those scrapers fetch and
  when feature 005's stale-marking logic is allowed to run.
- No new environment variables. Same `DISCORD_WEBHOOK_URL` /
  `NOTIFICATIONS_ENABLED` / `CINEMA_RECS_SOURCE_URL` configuration as
  prior features.

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

1. **Confirm a single run captures more than "today"/"this month"** —
   trigger an ingestion cycle and inspect the `showtime` table (or the
   web UI) for each cinema. Confirm showtimes exist for dates beyond
   tomorrow (Cinepolis) and beyond the current calendar month (Texas
   Theatre), captured in that one run — not requiring the job to run
   daily/monthly to accumulate them (spec User Story 1, SC-001, SC-004).

2. **Confirm the walk terminates itself, not on a fixed cutoff** — check
   the ingestion run's log output (`docker logs -f cinema-recs`) for
   Texas Theatre and Cinepolis; confirm each source's fetch stops once
   it hits its own "N consecutive empty periods" condition (research.md
   §1/§2) rather than after a hardcoded number of days/months, and that
   the showtimes captured count in the recorded `ingestion_run` row
   reflects everything from that walk (spec FR-002, FR-006).

3. **Confirm no false cancellation/reschedule from a narrow-window
   showing** — using a showtime dated several weeks out that a prior,
   narrower ingestion (pre-this-feature) had not re-touched recently,
   run a full-window ingestion cycle and confirm that showtime's
   `status` stays `active` (not `stale`) and no Discord
   cancellation/reschedule message fires for it, as long as the source
   still publishes it (spec User Story 2, SC-002).

4. **Confirm a genuine disappearance still alerts correctly** — remove a
   showtime from the source entirely (or simulate via direct DB edit
   like feature 005's quickstart) and confirm the existing
   cancellation/reschedule notification flow from feature 005 still
   fires exactly as before, now driven by full-window results (spec
   FR-005, User Story 2 Acceptance Scenario 2).

5. **Confirm a partial full-window failure doesn't corrupt existing
   data** — simulate a mid-walk failure (e.g. temporarily block network
   access to the source after the first page/date succeeds, or point
   `CINEMA_RECS_SOURCE_URL` at an unreachable host mid-test) and confirm:
   the `ingestion_run` row for that cycle is recorded as `failure` or
   `partial` with an error message identifying which page/date failed,
   and no previously-active showtime for that cinema was marked `stale`
   as a result of that run (spec User Story 3, SC-003).

See [data-model.md](./data-model.md) for how `IngestionRun.outcome` and
`error_message` are used to represent an incomplete full-window fetch,
and [research.md](./research.md) for each source's specific walk/stop
strategy.
