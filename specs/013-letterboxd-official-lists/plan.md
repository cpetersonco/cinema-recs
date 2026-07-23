# Implementation Plan: Letterboxd Official Lists as Recommendation Filters

**Branch**: `013-letterboxd-official-lists` | **Date**: 2026-07-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/013-letterboxd-official-lists/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Extend feature 003's fixed, built-in best-of-list recommendation
criterion from one list ("Official Top 250 Narrative Feature Films") to
nine, adding 8 curated official Letterboxd lists (Top 500, Most Fans,
Animated, Horror, Documentary, Women Directors, Black Directors,
Underseen — data-model.md). Technical approach: grow
`letterboxd_client.BUILT_IN_BEST_OF_LISTS` from `dict[str, str]` to
`dict[str, BestOfList]` (adding a human-readable `display_name` per
entry alongside the existing URL), and change `recommend.py`'s reason
token for a best-of match from the raw `best_of:{key}` string to that
list's `display_name`, so the existing free-text `reasons` column
(unchanged schema) surfaces real list names in the web view and Discord
notifications instead of internal keys. No new tables, routes, env vars,
or scheduler changes — `_refresh_reference_lists`'s existing per-list
try/except loop already scales to N lists (research.md).

## Technical Context

**Language/Version**: Python 3.11 (existing project standard)

**Primary Dependencies**: `curl_cffi` (existing Letterboxd client,
unchanged), Flask (existing web view, unchanged), `apscheduler`
(existing refresh scheduling, unchanged) — no new dependency introduced

**Storage**: SQLite (existing `cinema_recs.db`); no schema changes — see
data-model.md

**Testing**: pytest, network-isolated per Constitution Principle VIII
(existing `tests/unit/test_letterboxd_client.py` and
`tests/unit/test_recommend.py` mock the Letterboxd client boundary
already; new lists are tested the same way with canned fixtures)

**Target Platform**: Docker container on Unraid (existing deployment,
unchanged)

**Project Type**: Single project — existing `src/cinema_recs/` package,
`tests/unit/` + `tests/integration/`

**Performance Goals**: N/A beyond existing behavior — 8 additional
paginated list fetches (≤5 pages each per research.md) per scheduled
refresh cycle, well within the existing `REQUEST_PACING_SECONDS`/retry
budget already used for 1 list

**Constraints**: Must not make real network calls in the automated test
suite (Constitution Principle VIII); each onboarded list's markup must
be live-verified before being added (Constitution Principle VII, done in
research.md); a single list's fetch failure must not affect any other
list's cached data (existing FR-003-equivalent behavior, reused)

**Scale/Scope**: 8 additional built-in lists (9 total with the existing
one), each up to ~500 films; no operator-facing configuration surface
added (fixed set, code change to modify, per FR-005)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Python-First | All changes are Python (`letterboxd_client.py`, `recommend.py`); no new language/tooling | ✅ Pass |
| II. Docker-Native Deployment | No Dockerfile/compose changes needed — no new dependency, port, or volume | ✅ Pass |
| III. Unraid Runtime Compatibility | No new env vars/ports/volumes introduced (quickstart.md unchanged from feature 003's) | ✅ Pass |
| IV. Simplicity & Solo-Maintainer Ergonomics | Reuses feature 003's existing per-list dict/loop pattern exactly; no new abstraction, no operator-facing config surface added (fixed set, per FR-005) | ✅ Pass |
| V. Observability for Self-Hosting | Reuses existing per-list refresh success/failure log lines (`_refresh_reference_lists`), now covering 9 lists instead of 1 | ✅ Pass |
| VI. Explicit Over Inferred | Each list is an explicit, named dict entry (`list_key → BestOfList`) set at code-authoring time — no inference from URLs/names at runtime | ✅ Pass |
| VII. Live-Verify External Integrations | All 8 new list URLs live-verified during planning (research.md: 200 status, expected `data-target-link`/pagination markup) before being added to FR-001 | ✅ Pass |
| VIII. Network-Isolated Automated Tests | New/updated unit tests for `recommend.py` and `letterboxd_client.py` mock the HTTP boundary, consistent with existing tests in those files | ✅ Pass |
| IX. Backward-Compatible Schema Migrations | No schema change at all — this feature only changes in-code constants and string content, not the database | ✅ Pass (N/A) |

No violations. Complexity Tracking table not needed.

## Project Structure

### Documentation (this feature)

```text
specs/013-letterboxd-official-lists/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── best-of-list-interface.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/cinema_recs/
├── letterboxd_client.py   # BUILT_IN_BEST_OF_LISTS grows from dict[str, str]
│                           # to dict[str, BestOfList]; fetch_best_of_list_slugs
│                           # reused unchanged
├── recommend.py           # _refresh_reference_lists loop unchanged (already
│                           # iterates the dict generically); best-of match
│                           # token changes from best_of:{key} to display_name
├── storage.py              # unchanged (no schema change)
└── web.py                  # unchanged (reasons already rendered verbatim)

tests/
├── unit/
│   ├── test_letterboxd_client.py   # add fixtures/cases for the new list URLs
│   └── test_recommend.py           # add cases asserting display-name reasons
└── integration/
    └── test_web_view.py            # existing reasons-rendering coverage,
                                      # no new integration surface introduced
```

**Structure Decision**: Single existing project, no new modules or
directories. This feature is a targeted change to two existing files
(`letterboxd_client.py`'s constant, `recommend.py`'s reason-building
logic) plus corresponding unit test updates — consistent with the
Simplicity principle and feature 003's existing structure, which this
extends rather than replaces.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations — table not applicable.
