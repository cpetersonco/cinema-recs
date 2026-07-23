# Web View Contract (updated by feature 010)

Supersedes, for `GET /` only, the row-per-showtime shape described in
[feature 001's web-view contract](../../001-cinepolis-showtime-ingestion/contracts/web-view.md).
`GET /health` is unchanged (spec FR-008) — see that original contract
for it.

## `GET /`

Listing view of currently active showtimes, one venue section per
configured cinema.

**Response**: HTML page containing, per venue section, at most one row
per distinct movie title (spec FR-001) — never one row per individual
showtime. Each row represents that movie's single earliest upcoming
active showtime at that venue (spec FR-002) and includes:

- Movie title, show date, start time, format (unchanged from feature
  001's contract, omitted/shown as "—" if not provided by the source)
- A link to that showtime's ticket-purchase page, when the source
  provided one (spec FR-003); rendered as "—" (not an empty/broken
  link) when absent (spec FR-004)
- The movie's Letterboxd rating, rendered as a link to that movie's
  Letterboxd film page, when both a Letterboxd match and rating have
  been resolved (spec FR-005); rendered as "—" when either is missing
  (spec FR-006)
- Genre, poster, and "Recommended" indicators exactly as feature 002/003
  already define them (spec FR-007), now attached to the single
  consolidated row instead of repeated per showtime

**Empty state**: Unchanged from feature 001 — if no active showtimes
exist for a venue, the page renders a clear "no showtimes ingested yet"
message.

## Out of scope for this contract

- No authentication, no JSON API — same as feature 001's contract.
- No change to what showtime/rating data is captured or stored (spec
  FR-008) — this contract only describes how `GET /` presents data that
  already exists.
