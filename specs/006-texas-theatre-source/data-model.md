# Data Model: Texas Theatre Showtime Source

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Entities & Attributes

### 1. Cinema (Source Metadata)
Represents the venue record stored in the `cinemas` database table.

| Attribute | Type | Description | Constraints / Validation |
|-----------|------|-------------|---------------------------|
| `id` | Integer (Primary Key) | Internal database identifier | Auto-increment |
| `name` | String | Venue name | `"Texas Theatre"` |
| `location` | String | Geographic location | `"Oak Cliff, Dallas, TX"` |
| `source_url` | String | Target calendar URL | `"https://thetexastheatre.com/calendar"` |
| `created_at` | DateTime (UTC) | Timestamp when cinema record created | Non-null |

### 2. Showtime (Parsed Screening Session)
Represents an individual film screening or event session stored in the `showtimes` database table.

| Attribute | Type | Description | Constraints / Validation |
|-----------|------|-------------|---------------------------|
| `id` | Integer (Primary Key) | Internal database identifier | Auto-increment |
| `cinema_id` | Integer (Foreign Key) | Reference to `cinemas.id` | Foreign Key -> `cinemas.id` |
| `movie_title` | String | Film or event title | Non-empty string |
| `show_date` | Date | Date of screening | ISO 8601 YYYY-MM-DD |
| `start_time` | Time | Screening start time (local Central Time) | ISO 8601 HH:MM:SS |
| `format` | String (Optional) | Presentation format (e.g. `35mm`, `70mm`, `16mm`, `Digital`) | Nullable |
| `ticket_url` | String (Optional) | Direct event / ticketing link | Valid HTTP/HTTPS URL or null |
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

- **Uniqueness Constraint**: Unique index on `(cinema_id, movie_title, show_date, start_time)`.
- **One-to-Many**: `Cinema` (1) -> `Showtime` (N)
- **One-to-Many**: `Cinema` (1) -> `IngestionRun` (N)
