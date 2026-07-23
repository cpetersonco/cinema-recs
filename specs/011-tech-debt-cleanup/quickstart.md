# Quickstart: Tech Debt Cleanup — Cinema Routing, Deprecated APIs, Startup Coverage

## Prerequisites

- All prior features (001–010) already deployed — this feature changes internal reliability
  characteristics of code they all depend on (`ingest.py`'s dispatch, `storage.py`'s cinema
  registration, timestamp handling app-wide), not their externally-visible behavior.
- No new environment variables, ports, or volumes (spec FR-008) — same run command as before.

## Build and run

Same container, same run command as every prior feature — no new flags:

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

1. **Confirm existing deployments upgrade cleanly** — start the container against a database
   file created by a pre-feature-011 build (or, for local testing, a database already seeded
   with all 3 cinemas the old way). Confirm startup succeeds with no manual steps, and that a
   subsequent ingestion run for each of the 3 cinemas still uses its correct scraper (spot-check
   via each cinema's `/health` outcome and captured showtime count looking normal, not zero) —
   spec User Story 1 Edge Cases, SC-005.

2. **Confirm unrecognized sources fail loudly** — with a local/test database, insert (or
   configure) a cinema whose `source_type` doesn't match any known scraper and trigger an
   ingestion run for it. Confirm the run fails immediately with an error naming the unrecognized
   source type, and that no other cinema's scraper ran against it (spec User Story 1 Acceptance
   Scenario 2, SC-001).

3. **Confirm no deprecation warnings** — run the full automated test suite
   (`PYTHONPATH=src pytest tests/ -q`) and confirm no warnings reference the old UTC timestamp
   API (spec User Story 2, SC-002). Cross-check that timestamps recorded during a normal
   ingestion/notification cycle (e.g. an `ingestion_run.started_at`) still look correct and
   orderable, confirming no behavior change (spec FR-006).

4. **Confirm startup wiring has coverage** — run
   `PYTHONPATH=src pytest tests/unit/test_main.py -v` and confirm it includes passing tests for:
   all 3 cinemas ending up configured, the one-shot `ingest-once` CLI mode, and the default
   (server-starting) mode — without any test needing network access or a real running server
   (spec User Story 3, SC-003).

5. **Confirm nothing else regressed** — run the full suite
   (`PYTHONPATH=src pytest tests/ -q`) and confirm every previously-passing test still passes
   (spec SC-004).

See [data-model.md](./data-model.md) for the `Cinema.source_type` field and its migration, and
[research.md](./research.md) for the dispatch, timestamp, and test-coverage decisions.
