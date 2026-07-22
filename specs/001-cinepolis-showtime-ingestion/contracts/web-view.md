# Web View Contract

The only externally-facing interface for this feature is a minimal HTTP
view served by the Flask app, intended for the operator to check on the
system (spec FR-010, User Story 3, User Story 4).

## `GET /`

Listing view of currently active showtimes for the Cinepolis McKinney
cinema.

**Response**: HTML page containing, per showtime: movie title, show date,
start time, format (omitted or shown as "—" if not provided by the
source).

**Empty state**: If no active showtimes exist, the page MUST render a
clear "no showtimes ingested yet" message rather than an empty table with
no explanation (spec User Story 4, acceptance scenario 2).

## `GET /health`

Ingestion run health view.

**Response**: HTML (or plain text) page showing the most recent ingestion
run's outcome (`success` / `failure` / `partial`), the timestamp it ran,
and the number of showtimes captured. A `failure` outcome MUST be visibly
distinct from a `success` outcome that simply captured zero showtimes
(spec FR-009, User Story 3, acceptance scenario 2).

## Out of scope for this contract

- No authentication — this is a local/personal deployment on the
  operator's own network (per constitution's Simplicity principle; no
  multi-tenant or public-internet exposure is assumed).
- No JSON API — only the two HTML views above are required by the spec;
  a machine-readable API can be added later if a future feature needs one.
