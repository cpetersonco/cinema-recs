# Data Model: Angelika Film Center Dallas Showtime Source

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

No new tables or schema changes — this feature reuses the existing `cinemas`, `showtimes`, and
`ingestion_runs` tables shared by every source (Cinepolis, Texas Theatre). It adds one new row to
`cinemas` (the Angelika Dallas venue) and populates `showtimes`/`ingestion_runs` rows scoped to
that `cinema_id`, exactly like the Texas Theatre onboarding did.

## Entities & Attributes

### 1. Cinema (Source Metadata)
Represents the venue record stored in the `cinemas` database table.

| Attribute | Type | Description | Constraints / Validation |
|-----------|------|-------------|---------------------------|
| `id` | Integer (Primary Key) | Internal database identifier | Auto-increment |
| `name` | String | Venue name | `"Angelika Film Center Dallas"` |
| `location` | String | Geographic location | `"Dallas, TX"` |
| `source_url` | String | Target site URL | `"https://angelikafilmcenter.com/dallas"` |
| `created_at` | DateTime (UTC) | Timestamp when cinema record created | Non-null |

### 2. Showtime (Parsed Screening Session)
Represents an individual film screening stored in the `showtimes` database table.

| Attribute | Type | Description | Constraints / Validation |
|-----------|------|-------------|---------------------------|
| `id` | Integer (Primary Key) | Internal database identifier | Auto-increment |
| `cinema_id` | Integer (Foreign Key) | Reference to `cinemas.id` | Foreign Key -> `cinemas.id` |
| `movie_title` | String | Film title | Non-empty string |
| `show_date` | Date | Date of screening | ISO 8601 YYYY-MM-DD |
| `start_time` | Time | Screening start time (local Central Time) | ISO 8601 HH:MM:SS |
| `format` | String (Optional) | Presentation format (e.g. `Standard`, `3D`, `Special Event`) | Nullable |
| `ticket_url` | String (Optional) | Direct ticketing link | Valid HTTP/HTTPS URL or null |
| `first_seen_at` | DateTime (UTC) | Initial ingestion timestamp | Non-null |
| `last_seen_at` | DateTime (UTC) | Most recent ingestion timestamp | Non-null |
| `status` | String | Active status | `"active"` or `"stale"` |

### 3. IngestionRun (Run Log)
Represents an execution log stored in the `ingestion_runs` database table.

| Attribute | Type | Description | Constraints / Validation |
|-----------|------|-------------|---------------------------|
| `id` | Integer (Primary Key) | Internal database identifier | Auto-increment |
| `cinema_id` | Integer (Foreign Key) | Reference to `cinemas.id` | Foreign Key -> `cinemas.id` |
| `started_at` | DateTime (UTC) | Run start timestamp | Non-null |
| `finished_at` | DateTime (UTC) | Run completion timestamp | Nullable until finished |
| `outcome` | String | Summary outcome | `"success"`, `"failure"`, or `"partial"` |
| `showtimes_captured` | Integer | Total showtimes ingested | Non-negative integer |
| `error_message` | String (Optional) | Failure reason or partial warning | Nullable |

## Relationships & Uniqueness

- **Uniqueness Constraint**: Unique index on `(cinema_id, movie_title, show_date, start_time)` — already enforced by existing `storage.upsert_showtime`; the Angelika Dallas `cinema_id` naturally scopes its showtimes apart from Cinepolis and Texas Theatre.
- **One-to-Many**: `Cinema` (1) -> `Showtime` (N)
- **One-to-Many**: `Cinema` (1) -> `IngestionRun` (N)

## In-Memory Scrape Result Shape

Reuses the existing `scraper.py` types unchanged:

```python
class ScrapedShowtime(NamedTuple):
    movie_title: str
    show_date: date
    start_time: time
    format: str | None
    ticket_url: str | None

class ScrapeResult(NamedTuple):
    showtimes: list[ScrapedShowtime]
    reported_count: int
```
