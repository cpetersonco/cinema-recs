# Research: Tech Debt Cleanup — Cinema Routing, Deprecated APIs, Startup Coverage

## 1. Explicit cinema source-type identifier

**Current behavior**: `Cinema` (`models.py`) has `name`, `location`, `source_url` — no type
field. `ingest.py`'s `run_ingestion()` decides which scraper to call by substring-matching
`cinema.source_url`/`cinema.name`:

```python
if "thetexastheatre.com" in cinema.source_url.lower() or "texas theatre" in cinema.name.lower():
    result = scrape_texas_theatre_showtimes(cinema.source_url)
elif "angelikafilmcenter.com" in cinema.source_url.lower() or "angelika" in cinema.name.lower():
    result = scrape_angelika_dallas_showtimes(cinema.source_url)
else:
    result = scrape_showtimes(cinema.source_url)  # Cinepolis GraphQL scraper
```

This exact pattern is documented as intentional at the time — feature 008's
`contracts/scraper_interface.md` "Ingestion Dispatch Contract" section codifies it as "the
existing domain-substring dispatch pattern." It was a deliberate consistency choice for a
2-source app, not an oversight; it just never got revisited as a 3rd source made the `else`
branch's silent fallback a real risk (any future unrecognized source now falls through to the
Cinepolis-specific GraphQL scraper instead of failing).

**Decision**: Add a `source_type` column to the `cinema` table (`TEXT NOT NULL`, values
`"cinepolis"` | `"texas_theatre"` | `"angelika_dallas"`), set once at cinema-creation time via
`get_or_create_cinema`'s single call site (used by all three registration paths — the direct
Cinepolis call in `main.py` and the `ensure_texas_theatre_cinema`/`ensure_angelika_dallas_cinema`
wrappers in `storage.py`). `run_ingestion` dispatches on `cinema.source_type` via an explicit
mapping (dict or match statement), raising a clear error for any value not in that mapping
instead of defaulting to a scraper.

**Migration (FR-004)**: A new idempotent migration function (matching the existing
`_migrate_add_showtime_ticket_url`/`_migrate_add_notification_disappearance_columns` pattern in
`storage.py`) adds the column if absent, then backfills every existing row's `source_type` using
the *same* substring-matching logic being retired from `ingest.py` — one last use of the old
pattern, purely to assign existing rows their correct value once, not as ongoing dispatch logic.
New rows get their `source_type` explicitly from the caller (`get_or_create_cinema`'s new
parameter), never inferred.

**Rationale**: A single new column, set once at creation and read (not inferred) at dispatch
time, is the minimal change that satisfies FR-001–FR-004 — no new table, no new module. Backfilling
via the retiring logic is safe specifically because it's a one-time, one-directional operation
(old data → correct value) rather than an ongoing dependency on it.

**Alternatives considered**:
- A separate `source_type` lookup table with foreign key — rejected: unjustified complexity
  (Constitution IV) for 3 fixed values that don't need independent CRUD.
- Keep string-matching but tighten the patterns (e.g. require exact URL match) — rejected: still
  infers rather than states the type, and doesn't address the silent-fallback risk in the `else`
  branch, which is the actual finding (FR-003).
- A Python `Enum` class for the three values, stored as its `.value` string in SQLite — adopted as
  part of the above decision (not a separate alternative): gives dispatch code a closed,
  type-checked set of cases in `ingest.py` while storage stays plain `TEXT`, consistent with how
  every other string field in this schema is stored.

## 2. Removing the deprecated `datetime.utcnow()` call

**Current behavior**: 10 call sites across `ingest.py` (3), `storage.py` (6), `notify.py` (1) call
`datetime.utcnow()` directly, each producing a naive (no-tzinfo) UTC datetime that gets persisted
via `.isoformat()` and later parsed back via `datetime.fromisoformat()`, compared directly against
other naive datetimes (e.g. `mark_stale_showtimes`'s `last_seen_at < ?` SQL comparison on ISO
strings, and in-Python comparisons elsewhere).

**Decision**: Replace every `datetime.utcnow()` call with
`datetime.now(timezone.utc).replace(tzinfo=None)` — the direct, documented equivalent that
produces the exact same naive-UTC value `utcnow()` did, without calling the deprecated function.
No shared helper function is introduced; each of the 3 files already imports `datetime` from the
stdlib, so the fix is a mechanical per-call-site replacement (adding `timezone` to each file's
existing `from datetime import ...` line).

**Rationale**: FR-006 requires zero behavior change. Naively switching to
`datetime.now(timezone.utc)` (keeping the tzinfo) would produce *aware* datetimes that raise
`TypeError` when compared against the naive datetimes already flowing through
`datetime.fromisoformat()` round-trips elsewhere in the app (isoformat strings without a `+00:00`
offset parse back as naive) — that would be a real behavior change and a latent crash risk, not a
safe mechanical swap. `.replace(tzinfo=None)` after constructing the aware value keeps the
datetime naive while sourcing it from the non-deprecated API, which is the standard, minimal-diff
migration path off `utcnow()`.

**Alternatives considered**:
- Introduce a shared `_utcnow()` helper in a new `utils.py` — rejected: 10 call sites across 3
  files don't justify a new module (Constitution IV); the inline replacement is one line, not
  meaningfully more repetitive than importing and calling a helper would be.
- Switch the whole app to timezone-aware datetimes throughout (store `+00:00` offsets, compare
  aware-to-aware) — rejected: out of scope per FR-006/FR-008 (no behavior change) and a
  meaningfully larger change (every stored ISO string, every `fromisoformat()` call site, and any
  external consumer of the DB would need updating) than this feature's scope justifies.

## 3. Test coverage for `main.py`'s startup wiring

**Current behavior**: `main.py` has `bootstrap()` (loads config, initializes schema, registers
all 3 cinemas) and `main()` (calls `bootstrap()`, then either runs one ingestion/enrichment/
notification pass and returns — the `ingest-once` CLI mode — or does the same and then starts the
scheduler and the Flask server, which blocks forever). Neither has a test today; every other
module in the app has unit and/or integration tests.

**Decision**: Add `tests/unit/test_main.py` covering:
- `bootstrap()` directly: given required env vars set (via `monkeypatch.setenv`, mirroring
  `config.py`'s own test conventions) and a temp data dir, assert all 3 cinemas
  (Cinepolis, Texas Theatre, Angelika Dallas) come back configured with the correct
  `source_type` (ties directly to Finding 1's new field) and that `init_schema` was applied
  (tables queryable).
- The `ingest-once` CLI branch of `main()`: monkeypatch each scraper function
  (`scrape_showtimes`, `scrape_texas_theatre_showtimes`, `scrape_angelika_dallas_showtimes`) the
  same way `tests/unit/test_ingest.py` already does, and monkeypatch the network-calling
  dependencies of enrichment/recommendation/notification (TMDB client, Letterboxd client, Discord
  client — same seams `test_enrich.py`/`test_recommend.py`/`test_notify.py` already mock) so the
  whole pass runs against a temp SQLite DB with zero real network calls; assert it returns without
  starting the scheduler or the web server.
- The default (server-starting) branch: same mocking, plus monkeypatch `start_scheduler` and
  `Flask.run` (via `cinema_recs.web.create_app`'s returned app, or by monkeypatching
  `cinema_recs.scheduler.start_scheduler` and `flask.Flask.run` directly) to no-ops, then assert
  both were called with the expected `config`/`cinemas` arguments — proving the wiring is correct
  without actually blocking on a running server.

**Rationale**: This mirrors the mocking-at-the-network-boundary convention already established
throughout the test suite (`test_ingest.py` mocks scraper functions; `test_notify.py` mocks
`send_notification`; `test_recommend.py` mocks the Letterboxd client) rather than introducing a
new testing approach. No real network calls, no real blocking server — consistent with how every
other integration-style test in this repo already runs fully offline.

**Alternatives considered**:
- Spin up the real Flask dev server and Playwright-driven scrapers in a test and hit them for
  real — rejected: this is exactly the kind of live-network test the rest of the suite
  deliberately avoids (existing scraper tests use canned fixtures, not live sites); an
  end-to-end smoke test against the real internet belongs to manual/quickstart validation
  (as done for features 009/010), not the automated suite.
- Only test `bootstrap()`, skip testing `main()`'s CLI branching — rejected: FR-007 explicitly
  requires coverage of "what each supported command-line invocation mode actually does," and the
  branch logic (does it start the scheduler/server or not) is exactly the kind of wiring mistake
  this story exists to catch.
