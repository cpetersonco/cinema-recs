# Data Model: Cinepolis McKinney Showtime Ingestion

## Cinema

Represents a physical theater location. Only one row exists in this
phase (Cinepolis McKinney), but the shape supports more being added later
without redesign (spec FR-005, SC-005).

| Field | Type | Notes |
|---|---|---|
| `id` | integer, primary key | |
| `name` | text, not null | e.g. "Cinepolis McKinney" |
| `location` | text, not null | Human-readable address/location (off Highway 121, McKinney, TX) |
| `source_url` | text, not null | The Cinepolis showtimes page this cinema is scraped from |
| `created_at` | timestamp, not null | |

## Showtime

Represents a single scheduled screening at a cinema (spec FR-003,
FR-005, FR-006).

| Field | Type | Notes |
|---|---|---|
| `id` | integer, primary key | |
| `cinema_id` | integer, foreign key → Cinema.id, not null | |
| `movie_title` | text, not null | |
| `show_date` | date, not null | |
| `start_time` | time, not null | |
| `format` | text, nullable | e.g. "Standard", "VIP", "4DX"; null if source doesn't specify |
| `first_seen_at` | timestamp, not null | When this showtime was first ingested |
| `last_seen_at` | timestamp, not null | Updated on every ingestion run that still finds this showtime published |
| `status` | text, not null | `active` or `stale` (see lifecycle below) |

**Uniqueness rule**: `(cinema_id, movie_title, show_date, start_time, format)`
must be unique — this is the de-duplication key referenced in FR-006 and
SC-002.

**Lifecycle**:
- A showtime is inserted as `active` when first observed by an ingestion
  run.
- On each subsequent run, any previously `active` showtime still present
  in the freshly scraped set has `last_seen_at` updated; it remains
  `active`.
- Any previously `active` showtime NOT present in the freshly scraped set
  is transitioned to `stale` (FR-008, SC-003). Stale showtimes are
  retained for troubleshooting but excluded from the listing view.
- A showtime matching the uniqueness key of an existing `stale` row
  re-appearing in a later run transitions it back to `active` rather than
  inserting a duplicate row.

## Ingestion Run

Represents one execution of the showtime-fetching process (spec FR-009,
User Story 3).

| Field | Type | Notes |
|---|---|---|
| `id` | integer, primary key | |
| `cinema_id` | integer, foreign key → Cinema.id, not null | |
| `started_at` | timestamp, not null | |
| `finished_at` | timestamp, nullable | Null while still running |
| `outcome` | text, not null | `success`, `failure`, or `partial` (source reachable but some data missing) |
| `showtimes_captured` | integer, not null | Count of active showtimes after reconciliation, distinguishing "zero found" from "run failed" (FR-009) |
| `error_message` | text, nullable | Populated when `outcome` is `failure` or `partial` |

## Relationships

```
Cinema (1) ──< (many) Showtime
Cinema (1) ──< (many) IngestionRun
```

Every `Showtime` and `IngestionRun` row is scoped to a `Cinema`, so
onboarding a second cinema later only requires inserting a new `Cinema`
row and pointing a scraper/scheduler instance at it — no schema changes
(SC-005).
