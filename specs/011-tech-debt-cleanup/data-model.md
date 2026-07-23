# Data Model: Tech Debt Cleanup — Cinema Routing, Deprecated APIs, Startup Coverage

## Cinema (existing — `src/cinema_recs/models.py`, `storage.py`)

| Field | Change |
|---|---|
| `source_type` | **New** `str` field (`"cinepolis"` \| `"texas_theatre"` \| `"angelika_dallas"`). Set explicitly by the caller at creation time via `get_or_create_cinema`'s new required parameter (research.md §1) — never inferred from `name`/`source_url` after this feature. Backed by a new `TEXT NOT NULL` column, added via an idempotent migration (research.md §1) that backfills existing rows using the substring-matching logic being retired from `ingest.py`, run once. |

No other fields change. `name`, `location`, `source_url`, `created_at`, and the table's identity
as the single owning entity for "which cinema" remain exactly as they are today.

## No new entities

This feature adds one field to one existing entity and removes a deprecated API call — it
introduces no new tables, no new dataclasses, and no new persisted concepts beyond
`Cinema.source_type` above.

## Migration

`storage.py`'s `init_schema()` gains a third idempotent migration function alongside the existing
two (`_migrate_add_showtime_ticket_url`, `_migrate_add_notification_disappearance_columns`),
following the same `PRAGMA table_info` + conditional `ALTER TABLE` shape:

1. Add `source_type TEXT` to `cinema` if the column is absent (no-op on a fresh database, since
   `CREATE TABLE IF NOT EXISTS` for `cinema` includes it directly there).
2. For every existing row where `source_type IS NULL`, backfill it using the same
   substring-matching rules `ingest.py` used to dispatch on (`thetexastheatre.com`/`texas theatre`
   → `"texas_theatre"`; `angelikafilmcenter.com`/`angelika` → `"angelika_dallas"`; else →
   `"cinepolis"`), so an existing deployment's 3 cinemas end up with the same effective scraper
   they had before, with no operator action required (FR-004, SC-005).

No other table changes.

## State transitions

None introduced. `source_type` is set once at row creation (or backfilled once by the migration)
and never changes for the lifetime of a `Cinema` row — it is not a mutable operational status
field like `Showtime.status` or `IngestionRun.outcome`.
