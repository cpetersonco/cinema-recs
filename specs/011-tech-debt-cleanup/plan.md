# Implementation Plan: Tech Debt Cleanup — Cinema Routing, Deprecated APIs, Startup Coverage

**Branch**: `011-tech-debt-cleanup` | **Date**: 2026-07-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/011-tech-debt-cleanup/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

An architectural review of the codebase identified 7 tech-debt findings; this feature addresses
the 3 the review recommended acting on now, in that order. (1) `ingest.py` currently decides
which scraper to run for a cinema by substring-matching its name/URL, with an unrecognized source
silently falling back to the Cinepolis scraper — this becomes an explicit `Cinema.source_type`
field set once at creation, with dispatch on that field and a loud failure for anything
unrecognized, plus a one-time migration that backfills existing rows using the retiring
substring-matching logic so no deployment needs manual intervention. (2) 10 call sites across
`ingest.py`/`storage.py`/`notify.py` call the deprecated `datetime.utcnow()` — replaced with the
non-deprecated equivalent that produces the exact same naive-UTC value, so no downstream behavior
changes. (3) `main.py`'s startup wiring (which cinemas get configured, what each CLI mode does)
has zero test coverage today — closed with a new `tests/unit/test_main.py` that mocks the same
network boundaries (scrapers, TMDB/Letterboxd/Discord clients) the rest of the suite already
mocks, so it runs fully offline. No user-facing behavior, scraping logic, or configuration surface
changes (spec FR-008).

## Technical Context

**Language/Version**: Python 3.11 (per `pyproject.toml`; existing project standard, Constitution I)

**Primary Dependencies**: None new — pytest (existing) for the new `test_main.py`; no new runtime dependency for either the schema change or the timestamp fix (both use only the Python stdlib)

**Storage**: SQLite via the existing `src/cinema_recs/storage.py` module — one new column (`cinema.source_type`) added via a new idempotent migration function, following the existing two-migration pattern (data-model.md)

**Testing**: pytest (existing `tests/unit/` and `tests/integration/` suites); new `tests/unit/test_main.py` for `main.py`'s previously-uncovered startup wiring (research.md §3)

**Target Platform**: Linux server, Docker container on Unraid (existing deployment target, Constitution II/III) — unchanged by this feature

**Project Type**: Single Python application (existing `src/cinema_recs/` package) — unchanged

**Performance Goals**: No explicit new target; one additional column read at dispatch time and one one-time backfill migration are negligible against this app's existing per-cinema, per-refresh-interval workload

**Constraints**: No user-facing or configuration-surface change (spec FR-008) — this is an internal reliability/maintainability change only; existing deployments must upgrade with zero manual steps (spec FR-004, SC-005)

**Scale/Scope**: Same 3 existing cinemas, same single SQLite file; touches `ingest.py`, `storage.py` (schema + `get_or_create_cinema`/`ensure_*_cinema` call sites), `notify.py` (1 timestamp call site), and adds one new test file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Python-First**: PASS — all changes are within the existing `src/cinema_recs/` package; no second language introduced.
- **II. Docker-Native Deployment**: PASS — no new host dependencies, ports, or build steps; same `Dockerfile`/`docker run` invocation (quickstart.md).
- **III. Unraid Runtime Compatibility**: PASS — no new environment variables, volumes, or ports; existing config surface unchanged (spec FR-008).
- **IV. Simplicity & Solo-Maintainer Ergonomics**: PASS — the routing fix is one new column read explicitly rather than a new lookup table or dispatch framework (research.md §1); the timestamp fix is a mechanical per-call-site replacement, not a new shared helper module, since 10 call sites across 3 files don't justify one (research.md §2); the new tests reuse the exact network-boundary-mocking convention already used by every other integration-style test in this suite, introducing no new testing approach (research.md §3).
- **V. Observability for Self-Hosting**: PASS — an unrecognized cinema source now fails with a specific, actionable log/error message identifying the problem (spec FR-003), which is strictly more observable than today's silent misroute; no new failure modes are introduced elsewhere.

No violations requiring the Complexity Tracking table.

## Project Structure

### Documentation (this feature)

```text
specs/011-tech-debt-cleanup/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

No `contracts/` directory: this feature introduces no new external interface — no new API
endpoint, CLI flag, environment variable, or webhook payload shape (spec FR-008). It changes
internal dispatch, schema, and timestamp-handling behavior only.

### Source Code (repository root)

```text
src/cinema_recs/
├── models.py       # MODIFY: add `source_type: str` to the Cinema dataclass
├── storage.py       # MODIFY: add `source_type` column + migration (data-model.md);
│                    #   add `source_type` parameter to `get_or_create_cinema`;
│                    #   `ensure_texas_theatre_cinema`/`ensure_angelika_dallas_cinema`
│                    #   pass their known type explicitly; replace `datetime.utcnow()`
│                    #   at its 6 call sites in this file
├── ingest.py        # MODIFY: replace the if/elif/else substring-matching dispatch
│                    #   with an explicit mapping keyed on `cinema.source_type`, raising
│                    #   on an unrecognized value instead of defaulting to Cinepolis;
│                    #   replace `datetime.utcnow()` at its 3 call sites
├── notify.py        # MODIFY: replace `datetime.utcnow()` at its 1 call site
└── main.py           # MODIFY: pass Cinepolis's explicit `source_type` at its
                     #   `get_or_create_cinema` call site

tests/
└── unit/
    ├── test_ingest.py    # MODIFY: cover the new unrecognized-source-type failure path
    ├── test_storage.py    # MODIFY: cover the new column, migration/backfill, and the
    │                      #   `get_or_create_cinema`/`ensure_*_cinema` signature changes
    └── test_main.py        # NEW: startup wiring coverage (research.md §3) — previously
                           #   nonexistent
```

**Structure Decision**: No new modules — this is a targeted, mechanical set of changes across
5 existing files plus one new test file, matching the feature's own scope constraint (spec
FR-008: internal reliability change only, no new user-facing surface). All three findings
(routing, deprecated API, test coverage) touch different, mostly non-overlapping parts of the
same small set of files, so they're implemented as sequential edits rather than separate modules.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations — table intentionally omitted.
