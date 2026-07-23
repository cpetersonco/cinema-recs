# Data Model: Full Showtime Window Ingestion

No new persisted entities. This feature changes *how much* of a source's
calendar is fetched per run and *when* stale-marking is allowed to run,
not the shape of `Showtime` or `IngestionRun`. One existing field's
semantics is extended; no schema migration is required.

## Showtime (existing — `src/cinema_recs/models.py`, `storage.py`)

Unchanged fields. Behavioral change: `show_date` may now legitimately
hold dates far beyond "tomorrow" or "this calendar month" as a direct
result of a single ingestion run, since fetching is no longer bounded to
a single day/month per source.

## IngestionRun (existing — `src/cinema_recs/models.py`, `storage.py`)

| Field | Change |
|---|---|
| `outcome` | Existing values (`success`, `partial`, `failure`) are reused; `failure`/`partial` now also cover "the full-window walk (dates for Cinepolis, months for Texas Theatre) did not reach its own stop condition before erroring," per research.md §4 — not just "scrape raised" or "some entries were unparseable" as today. |
| `showtimes_captured` | Now reflects however many showtimes were successfully captured across *all* pages/dates fetched before either the walk completed or it failed partway through — not just a single day/month's count. |
| `error_message` | When a run fails partway through a multi-page/date walk, MUST describe which unit of work failed (e.g. "failed fetching Sep 2026 calendar page after 4 successful months") so the operator can tell a full-window failure apart from a single-page scrape failure in the existing log/DB record, per Constitution V (Observability). |

No new columns; existing `outcome`/`error_message` string fields already
accommodate this without a migration.

## New internal (non-persisted) concept: fetch completeness signal

Not a database entity — an in-memory signal threaded from each scraper's
multi-request loop back to `run_ingestion`, so it can gate whether
`storage.mark_stale_showtimes` is called (research.md §4, spec FR-003/
FR-004). Represented as part of each scraper's existing `ScrapeResult`
return value (e.g. an added boolean field), not a new table — this is an
implementation detail for the tasks/implementation phase, not a data
model change.

## State transitions (unchanged)

`Showtime.status`: `active` → `stale`, per feature 005, still driven
solely by `mark_stale_showtimes` comparing `last_seen_at` against the
current run's `started_at`. This feature does not change that
transition's logic — only the precondition (full-window fetch completed)
under which the comparison is allowed to run at all.
