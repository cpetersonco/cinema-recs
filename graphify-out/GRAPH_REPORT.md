# Graph Report - toasty-swinging-falcon  (2026-07-23)

## Corpus Check
- 167 files · ~129,119 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1653 nodes · 2262 edges · 102 communities (95 shown, 7 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 5 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ecf1fda3`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- storage.py
- run_enrichment
- run_notifications
- run_ingestion
- recommend.py
- test_web_view.py
- scraper.py
- Tasks: Cinepolis McKinney Showtime Ingestion (Alpha Cinema)
- Implementation Plan: Cinepolis McKinney Showtime Ingestion (Alpha Cinema)
- Implementation Plan: Showtime Notifications
- Implementation Plan: Movie Metadata Enrichment via TMDB
- Implementation Plan: Showtime Recommendation Rules
- 004-showtime-notifications/quickstart.md
- Implementation Plan: Showtime Cancellation & Reschedule Alerts
- Implementation Plan: Automatic CI/CD Deployment to Unraid
- Implementation Plan: Full Showtime Window Ingestion
- Tasks: [FEATURE NAME]
- speckit-analyze/SKILL.md
- Tasks: Movie Metadata Enrichment via TMDB
- Tasks: Showtime Recommendation Rules
- Tasks: Showtime Notifications
- parse_texas_theatre_html
- Tasks: Showtime Cancellation & Reschedule Alerts
- Tasks: Angelika Film Center Dallas Showtime Ingestion Source
- Tasks: Full Showtime Window Ingestion
- Tasks: Automatic CI/CD Deployment to Unraid
- Tasks: Texas Theatre Showtime Source Ingestion
- test_angelika_dallas_scraper.py
- One-time setup
- Research: Full Showtime Window Ingestion
- common.sh
- test_scraper.py
- Execution Steps
- run_recommendation_evaluation
- Research: Angelika Film Center Dallas Showtime Ingestion Source
- Feature Specification: [FEATURE NAME]
- Feature Specification: Texas Theatre Showtime Ingestion Source
- Feature Specification: Angelika Film Center Dallas Showtime Ingestion Source
- speckit-plan/SKILL.md
- speckit-specify/SKILL.md
- speckit-tasks/SKILL.md
- Core Principles
- Core Principles
- Phase 0 Research: Showtime Recommendation Rules
- Research: Texas Theatre Showtime Source Ingestion
- test_ingest.py
- Implementation Plan: [FEATURE]
- Phase 0 Research: Showtime Notifications
- speckit-checklist/SKILL.md
- README.md
- Phase 0 Research: Cinepolis McKinney Showtime Ingestion
- Implementation Plan: Texas Theatre Showtime Source Ingestion
- Scrape Function Interface
- Implementation Plan: Angelika Film Center Dallas Showtime Ingestion Source
- speckit-clarify/SKILL.md
- speckit-implement/SKILL.md
- create-new-feature.sh
- Phase 0 Research: Movie Metadata Enrichment via TMDB
- Data Model: Showtime Recommendation Rules
- Validation Scenarios
- Research: Automatic CI/CD Deployment to Unraid
- Data Model: Angelika Film Center Dallas Showtime Source
- Validation Scenarios
- speckit-constitution/SKILL.md
- 002-tmdb-metadata-enrichment/quickstart.md
- 003-showtime-recommendation-rules/quickstart.md
- Research: Showtime Cancellation & Reschedule Alerts
- Specification Quality Checklist: Texas Theatre Showtime Ingestion Source
- Scrape Function Interface
- Entities & Attributes
- Specification Quality Checklist: Angelika Film Center Dallas Showtime Ingestion Source
- speckit-taskstoissues/SKILL.md
- cinema-recs
- [CHECKLIST TYPE] Checklist: [FEATURE NAME]
- Web View Contract
- Data Model: Cinepolis McKinney Showtime Ingestion
- Data Model: Movie Metadata Enrichment via TMDB
- Quickstart: Movie Metadata Enrichment via TMDB
- Quickstart: Showtime Recommendation Rules
- 1. Site Platform & Fetch/Parse Method
- 1. Calendar Page Source & Parsing Method
- cinema-recs
- docker-entrypoint.sh
- check-prerequisites.sh
- setup-plan.sh
- setup-tasks.sh
- cinema-recs
- One-time setup
- Research: Consolidated Movie Listings with Ticket and Letterboxd Links
- Config
- Data Model: Tech Debt Cleanup — Cinema Routing, Deprecated APIs, Startup Coverage
- web.py
- main.py
- init_schema
- Cinema
- _ensure_letterboxd_data_cached

## God Nodes (most connected - your core abstractions)
1. `run_ingestion()` - 37 edges
2. `run_notifications()` - 31 edges
3. `get_connection()` - 27 edges
4. `ScrapeResult` - 25 edges
5. `ScrapedShowtime` - 24 edges
6. `run_recommendation_evaluation()` - 21 edges
7. `run_enrichment()` - 20 edges
8. `parse_cinemark_west_plano_html()` - 19 edges
9. `Config` - 17 edges
10. `_config()` - 17 edges

## Surprising Connections (you probably didn't know these)
- `mock_scrapers()` --calls--> `ScrapeResult`  [EXTRACTED]
  tests/unit/test_main.py → src/cinema_recs/scraper.py
- `test_looks_blocked_detects_cloudflare_interstitial()` --calls--> `looks_blocked()`  [EXTRACTED]
  tests/unit/test_scraper.py → src/cinema_recs/scraper.py
- `test_looks_blocked_false_for_normal_page()` --calls--> `looks_blocked()`  [EXTRACTED]
  tests/unit/test_scraper.py → src/cinema_recs/scraper.py
- `client()` --calls--> `create_app()`  [EXTRACTED]
  tests/integration/test_web_view.py → src/cinema_recs/web.py
- `test_listing_shows_one_row_per_venue_for_movie_playing_at_multiple_venues()` --calls--> `create_app()`  [EXTRACTED]
  tests/integration/test_web_view.py → src/cinema_recs/web.py

## Import Cycles
- None detected.

## Communities (102 total, 7 thin omitted)

### Community 0 - "storage.py"
Cohesion: 0.05
Nodes (79): Connection, Flask, bootstrap(), _log_run(), main(), _run_enrichment(), _run_ingestion_all(), _run_notifications_all() (+71 more)

### Community 1 - "run_enrichment"
Cohesion: 0.09
Nodes (45): BackgroundScheduler, _candidate_titles(), The raw title first, then an event-suffix-stripped variant if that     actually, Enrich every distinct movie title with no movie_metadata row yet     (spec FR-00, run_enrichment(), start_scheduler(), get_movie_details(), _get_with_retry() (+37 more)

### Community 2 - "run_notifications"
Cohesion: 0.08
Nodes (46): Config, load_config(), _load_letterboxd_rating_threshold(), _load_notifications_enabled(), Invalid/non-numeric values are treated as unset (spec FR-008),     never as a st, Enabled by default once a webhook URL is configured — the switch     exists to p, POST a plain-text message to a Discord webhook. Raises on any     non-2xx respon, send_notification() (+38 more)

### Community 3 - "run_ingestion"
Cohesion: 0.08
Nodes (38): NamedTuple, run_ingestion(), Fetch every showtime Cinemark West Plano currently has published,     across eve, scrape_cinemark_west_plano_showtimes(), ScrapedShowtime, ScrapeResult, test_angelika_dallas_ingestion_end_to_end(), test_angelika_dallas_ingestion_records_failure_outcome() (+30 more)

### Community 4 - "recommend.py"
Cohesion: 0.14
Nodes (30): Response, fetch_best_of_list_slugs(), fetch_movie_rating(), _fetch_paginated_slugs(), fetch_watchlist_slugs(), _get_with_retry(), _raise_for_unexpected_status(), Scrape film slugs from a paginated Letterboxd poster grid (a     watchlist or li (+22 more)

### Community 6 - "scraper.py"
Cohesion: 0.16
Nodes (24): Any, RuntimeError, BlockedError, _click_angelika_date_with_retry(), _extract_angelika_labeled_dates(), fetch_angelika_dallas_films(), _fetch_page_html_with_retry(), fetch_showings_json() (+16 more)

### Community 7 - "Tasks: Cinepolis McKinney Showtime Ingestion (Alpha Cinema)"
Cohesion: 0.06
Nodes (31): Dependencies & Execution Order, Format: `[ID] [P?] [Story] Description`, Implementation for this Amendment, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation for User Story 4, Implementation Strategy (+23 more)

### Community 8 - "Implementation Plan: Cinepolis McKinney Showtime Ingestion (Alpha Cinema)"
Cohesion: 0.06
Nodes (28): Content Quality, Feature Readiness, Notes, Requirement Completeness, Specification Quality Checklist: Cinepolis McKinney Showtime Ingestion (Alpha Cinema), Complexity Tracking, Constitution Check, Documentation (this feature) (+20 more)

### Community 9 - "Implementation Plan: Showtime Notifications"
Cohesion: 0.06
Nodes (28): Content Quality, Feature Readiness, Notes, Requirement Completeness, Specification Quality Checklist: Showtime Notifications, Complexity Tracking, Constitution Check, Documentation (this feature) (+20 more)

### Community 10 - "Implementation Plan: Movie Metadata Enrichment via TMDB"
Cohesion: 0.07
Nodes (27): Content Quality, Feature Readiness, Notes, Requirement Completeness, Specification Quality Checklist: Movie Metadata Enrichment via TMDB, Complexity Tracking, Constitution Check, Documentation (this feature) (+19 more)

### Community 11 - "Implementation Plan: Showtime Recommendation Rules"
Cohesion: 0.07
Nodes (27): Content Quality, Feature Readiness, Notes, Requirement Completeness, Specification Quality Checklist: Showtime Recommendation Rules, Complexity Tracking, Constitution Check, Documentation (this feature) (+19 more)

### Community 12 - "004-showtime-notifications/quickstart.md"
Cohesion: 0.07
Nodes (23): Interface Contract: Discord Notification Delivery, Outbound: Discord webhook `POST {DISCORD_WEBHOOK_URL}`, Data Model: Showtime Notifications, Notification Configuration, Notification Record, Relationships, Build and run, Configuration (new environment variables, both optional) (+15 more)

### Community 13 - "Implementation Plan: Showtime Cancellation & Reschedule Alerts"
Cohesion: 0.07
Nodes (26): Content Quality, Feature Readiness, Notes, Requirement Completeness, Specification Quality Checklist: Showtime Cancellation & Reschedule Alerts, Complexity Tracking, Constitution Check, Documentation (this feature) (+18 more)

### Community 14 - "Implementation Plan: Automatic CI/CD Deployment to Unraid"
Cohesion: 0.07
Nodes (25): Content Quality, Feature Readiness, Notes, Requirement Completeness, Specification Quality Checklist: Automatic CI/CD Deployment to Unraid, Complexity Tracking, Constitution Check, Documentation (this feature) (+17 more)

### Community 15 - "Implementation Plan: Full Showtime Window Ingestion"
Cohesion: 0.07
Nodes (25): Content Quality, Feature Readiness, Notes, Requirement Completeness, Specification Quality Checklist: Full Showtime Window Ingestion, Complexity Tracking, Constitution Check, Documentation (this feature) (+17 more)

### Community 16 - "Tasks: [FEATURE NAME]"
Cohesion: 0.07
Nodes (26): Dependencies & Execution Order, Format: `[ID] [P?] [Story] Description`, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Strategy, Incremental Delivery, MVP First (User Story 1 Only) (+18 more)

### Community 17 - "speckit-analyze/SKILL.md"
Cohesion: 0.08
Nodes (25): 1. Initialize Analysis Context, 2. Load Artifacts (Progressive Disclosure), 3. Build Semantic Models, 4. Detection Passes (Token-Efficient Analysis), 5. Severity Assignment, 6. Produce Compact Analysis Report, 7. Provide Next Actions, 8. Offer Remediation (+17 more)

### Community 18 - "Tasks: Movie Metadata Enrichment via TMDB"
Cohesion: 0.08
Nodes (25): Dependencies & Execution Order, Format: `[ID] [P?] [Story] Description`, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Strategy, Incremental Delivery, MVP First (User Story 1 Only) (+17 more)

### Community 19 - "Tasks: Showtime Recommendation Rules"
Cohesion: 0.08
Nodes (24): Dependencies & Execution Order, Format: `[ID] [P?] [Story] Description`, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Strategy, Incremental Delivery, MVP First (User Story 1 Only) (+16 more)

### Community 20 - "Tasks: Showtime Notifications"
Cohesion: 0.08
Nodes (24): Dependencies & Execution Order, Format: `[ID] [P?] [Story] Description`, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Strategy, Incremental Delivery, MVP First (User Story 1 Only) (+16 more)

### Community 21 - "parse_texas_theatre_html"
Cohesion: 0.14
Nodes (24): BeautifulSoup, _extract_calendar_year(), extract_format(), extract_next_month_url(), is_non_film_event(), _parse_listing_date(), parse_texas_theatre_html(), The calendar page's <title> is "<Month> <Year> | The Texas Theatre"     (e.g. "J (+16 more)

### Community 22 - "Tasks: Showtime Cancellation & Reschedule Alerts"
Cohesion: 0.08
Nodes (23): Dependencies & Execution Order, Format: `[ID] [P?] [Story] Description`, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Strategy, Incremental Delivery, MVP First (User Story 1 Only) (+15 more)

### Community 23 - "Tasks: Angelika Film Center Dallas Showtime Ingestion Source"
Cohesion: 0.08
Nodes (23): Dependencies & Execution Order, Format: `[ID] [P?] [Story] Description`, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Strategy, Incremental Delivery, MVP First (User Story 1 Only) (+15 more)

### Community 24 - "Tasks: Full Showtime Window Ingestion"
Cohesion: 0.08
Nodes (23): Dependencies & Execution Order, Format: `[ID] [P?] [Story] Description`, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Strategy, Incremental Delivery, MVP First (User Story 1 Only) (+15 more)

### Community 25 - "Tasks: Automatic CI/CD Deployment to Unraid"
Cohesion: 0.09
Nodes (21): Dependencies & Execution Order, Format: `[ID] [P?] [Story] Description`, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Strategy, Incremental Delivery, MVP First (User Story 1 Only) (+13 more)

### Community 26 - "Tasks: Texas Theatre Showtime Source Ingestion"
Cohesion: 0.10
Nodes (20): Dependencies & Execution Order, Format: `[ID] [P?] [Story] Description`, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Strategy, MVP First (User Story 1 Only), Phase 1: Setup (Shared Infrastructure) (+12 more)

### Community 27 - "test_angelika_dallas_scraper.py"
Cohesion: 0.16
Nodes (19): parse_angelika_dallas_films(), _parse_angelika_date_strip_label(), _parse_angelika_datetime(), Labels are like "Today, 7/23", "Tomorrow, 7/24", "Sunday 7/26" —     always mont, Fold the already-captured initial page load's payload (covering     `labeled_dat, Map a `/films` API response into showtime records.      The endpoint returns fil, _walk_angelika_dallas_dates(), _payload_for_date() (+11 more)

### Community 28 - "One-time setup"
Cohesion: 0.11
Nodes (15): GitHub Actions workflow: `.github/workflows/deploy.yml`, `/health` endpoint (extended), Interface Contract: CI/CD Pipeline & Version Endpoint, Watchtower ↔ GHCR ↔ `cinema-recs` container, Container Image, Data Model: Automatic CI/CD Deployment to Unraid, Deployment/Update Event, 1. GitHub Actions (no secrets to create) (+7 more)

### Community 29 - "Research: Full Showtime Window Ingestion"
Cohesion: 0.11
Nodes (15): Data Model: Full Showtime Window Ingestion, IngestionRun (existing — `src/cinema_recs/models.py`, `storage.py`), New internal (non-persisted) concept: fetch completeness signal, Showtime (existing — `src/cinema_recs/models.py`, `storage.py`), State transitions (unchanged), Build and run, Prerequisites, Quickstart: Full Showtime Window Ingestion (+7 more)

### Community 30 - "common.sh"
Cohesion: 0.13
Nodes (5): get_feature_paths(), get_repo_root(), _persist_feature_json(), resolve_specify_init_dir(), common.sh script

### Community 31 - "test_scraper.py"
Cohesion: 0.19
Nodes (18): parse_showings_response(), Map a `showingsForDate` GraphQL response into showtime records.      NOTE: This, Walk forward one date at a time from `start_date`, calling     `query_date_fn(d), _walk_cinepolis_dates(), _entry(), _response(), test_looks_blocked_detects_cloudflare_interstitial(), test_looks_blocked_false_for_normal_page() (+10 more)

### Community 32 - "Execution Steps"
Cohesion: 0.12
Nodes (15): 1. Initialize Convergence Context, 2. Load Artifacts (Progressive Disclosure), 3. Build the Intent Inventory, 4. Assess the Codebase and Classify Findings, 5. Assign Severity, 6. Present the In-Session Findings Summary, 7. Append Convergence Tasks (or report converged), 8. Provide Next Actions (Handoff) (+7 more)

### Community 33 - "run_recommendation_evaluation"
Cohesion: 0.07
Nodes (25): Content Quality, Feature Readiness, Notes, Requirement Completeness, Specification Quality Checklist: Tech Debt Cleanup — Cinema Routing, Deprecated APIs, Startup Coverage, Complexity Tracking, Constitution Check, Documentation (this feature) (+17 more)

### Community 34 - "Research: Angelika Film Center Dallas Showtime Ingestion Source"
Cohesion: 0.14
Nodes (14): 2. Presentation Format Extraction, 3. Timezone & DateTime Handling, 4. Deduplication & Idempotency, 5. Non-Film Event Filtering, Alternatives Considered, Decision, Decision (Confirmed), Decision (Confirmed) (+6 more)

### Community 35 - "Feature Specification: [FEATURE NAME]"
Cohesion: 0.15
Nodes (12): Assumptions, Edge Cases, Feature Specification: [FEATURE NAME], Functional Requirements, Key Entities *(include if feature involves data)*, Measurable Outcomes, Requirements *(mandatory)*, Success Criteria *(mandatory)* (+4 more)

### Community 36 - "Feature Specification: Texas Theatre Showtime Ingestion Source"
Cohesion: 0.17
Nodes (12): Assumptions, Edge Cases, Feature Specification: Texas Theatre Showtime Ingestion Source, Functional Requirements, Key Entities, Measurable Outcomes, Requirements *(mandatory)*, Success Criteria *(mandatory)* (+4 more)

### Community 37 - "Feature Specification: Angelika Film Center Dallas Showtime Ingestion Source"
Cohesion: 0.17
Nodes (12): Assumptions, Edge Cases, Feature Specification: Angelika Film Center Dallas Showtime Ingestion Source, Functional Requirements, Key Entities, Measurable Outcomes, Requirements *(mandatory)*, Success Criteria *(mandatory)* (+4 more)

### Community 38 - "speckit-plan/SKILL.md"
Cohesion: 0.18
Nodes (10): Completion Report, Done When, Key rules, Mandatory Post-Execution Hooks, Outline, Phase 0: Outline & Research, Phase 1: Design & Contracts, Phases (+2 more)

### Community 39 - "speckit-specify/SKILL.md"
Cohesion: 0.18
Nodes (10): Completion Report, Done When, For AI Generation, Mandatory Post-Execution Hooks, Outline, Pre-Execution Checks, Quick Guidelines, Section Requirements (+2 more)

### Community 40 - "speckit-tasks/SKILL.md"
Cohesion: 0.18
Nodes (10): Checklist Format (REQUIRED), Completion Report, Done When, Mandatory Post-Execution Hooks, Outline, Phase Structure, Pre-Execution Checks, Task Generation Rules (+2 more)

### Community 41 - "Core Principles"
Cohesion: 0.18
Nodes (10): Cinema Recs Constitution, Core Principles, Development Workflow, Governance, I. Python-First, II. Docker-Native Deployment, III. Unraid Runtime Compatibility, IV. Simplicity & Solo-Maintainer Ergonomics (+2 more)

### Community 42 - "Core Principles"
Cohesion: 0.18
Nodes (10): Core Principles, Governance, [PRINCIPLE_1_NAME], [PRINCIPLE_2_NAME], [PRINCIPLE_3_NAME], [PRINCIPLE_4_NAME], [PRINCIPLE_5_NAME], [PROJECT_NAME] Constitution (+2 more)

### Community 43 - "Phase 0 Research: Showtime Recommendation Rules"
Cohesion: 0.18
Nodes (10): Decision: A dedicated `letterboxd.com/search/...` lookup is NOT used, Decision: Built-in best-of list URL for "Official Top 250 Narrative Feature Films", Decision: Cache per-movie Letterboxd data (slug + rating); always re-fetch watchlist/best-of-list membership, Decision: Config takes effect via container restart, not live-reload, Decision: Invalid rating threshold parsing (FR-008), Decision: Plain `requests` against Letterboxd's public pages (no headless browser, no HTML-parsing library), Decision: Recommendation evaluation runs on the same schedule as ingestion/enrichment, Decision: Resolving an apparent conflict between FR-003(c) and FR-005/SC-004 (+2 more)

### Community 44 - "Research: Texas Theatre Showtime Source Ingestion"
Cohesion: 0.18
Nodes (11): 1. Calendar Page Source & Parsing Method, 3. Timezone & DateTime Handling, 4. Deduplication & Idempotency, Alternatives Considered, Decision, Decision, Decision, Rationale (+3 more)

### Community 45 - "test_ingest.py"
Cohesion: 0.07
Nodes (25): Content Quality, Feature Readiness, Notes, Requirement Completeness, Specification Quality Checklist: Consolidated Movie Listings with Ticket and Letterboxd Links, Complexity Tracking, Constitution Check, Documentation (this feature) (+17 more)

### Community 47 - "Implementation Plan: [FEATURE]"
Cohesion: 0.22
Nodes (8): Complexity Tracking, Constitution Check, Documentation (this feature), Implementation Plan: [FEATURE], Project Structure, Source Code (repository root), Summary, Technical Context

### Community 48 - "Phase 0 Research: Showtime Notifications"
Cohesion: 0.22
Nodes (8): Decision: No retry-with-backoff on webhook delivery failure, Decision: Notification content format, Decision: Notification identity and dedup is per-movie, not per-showtime, Decision: Plain `requests.post()` against Discord's webhook URL (no Discord SDK), Decision: Ticket link (FR-002a) requires no new data source, Decision: Two independent config knobs — webhook URL and an enabled flag, Decision: Which showtime's date/time appears in the notification, Phase 0 Research: Showtime Notifications

### Community 49 - "speckit-checklist/SKILL.md"
Cohesion: 0.25
Nodes (7): Anti-Examples: What NOT To Do, Checklist Purpose: "Unit Tests for English", Example Checklist Types & Sample Items, Execution Steps, Post-Execution Checks, Pre-Execution Checks, User Input

### Community 50 - "README.md"
Cohesion: 0.40
Nodes (5): Build and run, Configuration (environment variables), Prerequisites, Quickstart: Cinepolis McKinney Showtime Ingestion, Validate it works

### Community 51 - "Phase 0 Research: Cinepolis McKinney Showtime Ingestion"
Cohesion: 0.25
Nodes (7): Decision: Cinepolis' own GraphQL API via a stealth-Playwright-loaded session, Decision: Flask for the minimal listing view, Decision: In-process scheduling via `APScheduler`, Decision: `pytest` with fetch/parse kept separate for testing, Decision: SQLite for storage, Decision: Ticket URL (FR-011) is constructed from the existing `id` field — no new API/scrape needed, Phase 0 Research: Cinepolis McKinney Showtime Ingestion

### Community 52 - "Implementation Plan: Texas Theatre Showtime Source Ingestion"
Cohesion: 0.25
Nodes (8): Complexity Tracking, Constitution Check, Documentation (this feature), Implementation Plan: Texas Theatre Showtime Source Ingestion, Project Structure, Source Code Layout, Summary, Technical Context

### Community 53 - "Scrape Function Interface"
Cohesion: 0.25
Nodes (8): Cinema Registration Contract, Error Behaviors, Function Signature, Ingestion Dispatch Contract, Input Parameters, Interface Contract: Angelika Film Center Dallas Scraper, Return Value (`ScrapeResult`), Scrape Function Interface

### Community 54 - "Implementation Plan: Angelika Film Center Dallas Showtime Ingestion Source"
Cohesion: 0.25
Nodes (8): Complexity Tracking, Constitution Check, Documentation (this feature), Implementation Plan: Angelika Film Center Dallas Showtime Ingestion Source, Project Structure, Source Code (repository root), Summary, Technical Context

### Community 55 - "speckit-clarify/SKILL.md"
Cohesion: 0.29
Nodes (6): Completion Report, Done When, Mandatory Post-Execution Hooks, Outline, Pre-Execution Checks, User Input

### Community 56 - "speckit-implement/SKILL.md"
Cohesion: 0.29
Nodes (6): Completion Report, Done When, Mandatory Post-Execution Hooks, Outline, Pre-Execution Checks, User Input

### Community 57 - "create-new-feature.sh"
Cohesion: 0.38
Nodes (3): get_highest_from_specs(), is_feature_number_in_range(), create-new-feature.sh script

### Community 58 - "Phase 0 Research: Movie Metadata Enrichment via TMDB"
Cohesion: 0.29
Nodes (6): Decision: Fixed-delay pacing instead of a rate-limiting algorithm, Decision: Naive title-similarity matching (normalized exact / clear top result), Decision: Plain `requests` against TMDB's public REST API, Decision: TMDB identifier as the sole hand-off to feature 003, Decision: `unittest.mock.patch` (stdlib) for testing TMDB calls, Phase 0 Research: Movie Metadata Enrichment via TMDB

### Community 59 - "Data Model: Showtime Recommendation Rules"
Cohesion: 0.29
Nodes (7): Cross-feature note (feature 004), Data Model: Showtime Recommendation Rules, Letterboxd Movie Data, Letterboxd Reference List (cache), Movie Recommendation, Recommendation Configuration, Relationships

### Community 60 - "Validation Scenarios"
Cohesion: 0.29
Nodes (7): Automated Unit & Integration Tests, Prerequisites, Quickstart & Validation Guide: Texas Theatre Showtime Ingestion, Scenario 1: Run Ingestion against Texas Theatre Calendar, Scenario 2: Validate Ingested Showtimes and Projection Formats, Scenario 3: Verify Idempotency on Re-Run, Validation Scenarios

### Community 61 - "Research: Automatic CI/CD Deployment to Unraid"
Cohesion: 0.29
Nodes (6): Decision: Publish images to GHCR as public (repo is already public), Decision: Pull-based update via Watchtower polling GHCR, not a push from GitHub Actions, Decision: Test suite runs inside the same Playwright base image as production, Decision: Version visibility via a build-time `GIT_SHA` baked into the image, surfaced on `/health`, Decision: Watchtower scoped via container label, not blanket host-wide auto-update, Research: Automatic CI/CD Deployment to Unraid

### Community 62 - "Data Model: Angelika Film Center Dallas Showtime Source"
Cohesion: 0.29
Nodes (7): 1. Cinema (Source Metadata), 2. Showtime (Parsed Screening Session), 3. IngestionRun (Run Log), Data Model: Angelika Film Center Dallas Showtime Source, Entities & Attributes, In-Memory Scrape Result Shape, Relationships & Uniqueness

### Community 63 - "Validation Scenarios"
Cohesion: 0.29
Nodes (7): Automated Unit & Integration Tests, Prerequisites, Quickstart & Validation Guide: Angelika Film Center Dallas Showtime Ingestion, Scenario 1: Run Ingestion against Angelika Film Center Dallas, Scenario 2: Validate Ingested Showtimes and Presentation Formats, Scenario 3: Verify Idempotency on Re-Run, Validation Scenarios

### Community 64 - "speckit-constitution/SKILL.md"
Cohesion: 0.33
Nodes (5): Outline, Post-Execution Checks, Pre-Execution Checks, Scope Guard, User Input

### Community 65 - "002-tmdb-metadata-enrichment/quickstart.md"
Cohesion: 0.18
Nodes (8): Internal Interface Contract: Movie Metadata Lookup, `storage.get_movie_metadata(db_path, movie_title) -> MovieMetadata | None`, Web View Extension (`GET /`), Build and run, Configuration (new environment variable), Prerequisites, Quickstart: Movie Metadata Enrichment via TMDB, Validate it works

### Community 66 - "003-showtime-recommendation-rules/quickstart.md"
Cohesion: 0.18
Nodes (8): Internal Interface Contract: Movie Recommendation Lookup, `storage.get_movie_recommendation(db_path, movie_title) -> MovieRecommendation | None`, Web View Extension (`GET /`), Build and run, Configuration (new environment variables, both optional), Prerequisites, Quickstart: Showtime Recommendation Rules, Validate it works

### Community 67 - "Research: Showtime Cancellation & Reschedule Alerts"
Cohesion: 0.33
Nodes (5): Decision: Classify cancelled vs. rescheduled via `get_next_showtime_for_movie`, reused as-is, Decision: Detect disappearance by re-checking the referenced showtime's status, not by diffing scrape output, Decision: Extend `notification_record` with additive columns, not a new table, Decision: Run disappearance detection inside `notify.py`'s existing `run_notifications()`, as a second pass after the existing recommendation pass, Research: Showtime Cancellation & Reschedule Alerts

### Community 68 - "Specification Quality Checklist: Texas Theatre Showtime Ingestion Source"
Cohesion: 0.33
Nodes (5): Content Quality, Feature Readiness, Notes, Requirement Completeness, Specification Quality Checklist: Texas Theatre Showtime Ingestion Source

### Community 70 - "Scrape Function Interface"
Cohesion: 0.33
Nodes (6): Error Behaviors, Function Signature, Input Parameters, Interface Contract: Texas Theatre Scraper, Return Value (`ScraperResult`), Scrape Function Interface

### Community 71 - "Entities & Attributes"
Cohesion: 0.33
Nodes (6): 1. Cinema (Source Metadata), 2. Showtime (Parsed Screening Session), 3. IngestionRun (Run Log), Data Model: Texas Theatre Showtime Source, Entities & Attributes, Relationships & Uniqueness

### Community 72 - "Specification Quality Checklist: Angelika Film Center Dallas Showtime Ingestion Source"
Cohesion: 0.33
Nodes (5): Content Quality, Feature Readiness, Notes, Requirement Completeness, Specification Quality Checklist: Angelika Film Center Dallas Showtime Ingestion Source

### Community 74 - "speckit-taskstoissues/SKILL.md"
Cohesion: 0.40
Nodes (4): Outline, Post-Execution Checks, Pre-Execution Checks, User Input

### Community 75 - "cinema-recs"
Cohesion: 0.25
Nodes (5): cinema-recs, Deployment (CI/CD), How showtime fetching works, Local development, Quickstart

### Community 76 - "[CHECKLIST TYPE] Checklist: [FEATURE NAME]"
Cohesion: 0.40
Nodes (4): [Category 1], [Category 2], [CHECKLIST TYPE] Checklist: [FEATURE NAME], Notes

### Community 77 - "Web View Contract"
Cohesion: 0.20
Nodes (8): Data Model: Consolidated Movie Listings with Ticket and Letterboxd Links, Existing entities used (unchanged), New internal (non-persisted) concept: consolidated listing row, Template rendering changes, Build and run, Prerequisites, Quickstart: Consolidated Movie Listings with Ticket and Letterboxd Links, Validate it works

### Community 78 - "Data Model: Cinepolis McKinney Showtime Ingestion"
Cohesion: 0.40
Nodes (5): Cinema, Data Model: Cinepolis McKinney Showtime Ingestion, Ingestion Run, Relationships, Showtime

### Community 79 - "Data Model: Movie Metadata Enrichment via TMDB"
Cohesion: 0.09
Nodes (21): Dependencies & Execution Order, Format: `[ID] [P?] [Story] Description`, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Strategy, Incremental Delivery, MVP First (User Story 1 Only) (+13 more)

### Community 80 - "Quickstart: Movie Metadata Enrichment via TMDB"
Cohesion: 0.05
Nodes (42): Content Quality, Feature Readiness, Notes, Requirement Completeness, Specification Quality Checklist: Cinemark West Plano XD and ScreenX Showtime Ingestion Source, Error Behaviors, Function Signature, Ingestion Dispatch Contract (+34 more)

### Community 81 - "Quickstart: Showtime Recommendation Rules"
Cohesion: 0.08
Nodes (26): 1. Site Platform & Fetch/Parse Method, 2. Presentation Format Extraction (including 70mm), 3. Ticket URL & Showtime Identity, 4. Date Window Discovery, 5. Timezone & DateTime Handling, 6. Non-Film Events, 7. Deduplication & Idempotency, Alternatives Considered (+18 more)

### Community 82 - "1. Site Platform & Fetch/Parse Method"
Cohesion: 0.40
Nodes (5): 1. Site Platform & Fetch/Parse Method, Alternatives Considered, Confirmed via Live Network Inspection (2026-07-22), Decision, Rationale

### Community 83 - "1. Calendar Page Source & Parsing Method"
Cohesion: 0.10
Nodes (20): Dependencies & Execution Order, Format: `[ID] [P?] [Story] Description`, Implementation for User Story 1, Implementation for User Story 2, Implementation Strategy, Incremental Delivery, MVP First (User Story 1 Only), Notes (+12 more)

### Community 93 - "One-time setup"
Cohesion: 0.08
Nodes (23): Dependencies & Execution Order, Format: `[ID] [P?] [Story] Description`, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Strategy, Incremental Delivery, MVP First (User Story 1 + User Story 2, both P1) (+15 more)

### Community 94 - "Research: Consolidated Movie Listings with Ticket and Letterboxd Links"
Cohesion: 0.33
Nodes (5): 1. How to pick "the" showtime a consolidated row represents, 2. Ticket link source, 3. Letterboxd rating + link source, 4. Grouping scope: per cinema section, not across cinemas, Research: Consolidated Movie Listings with Ticket and Letterboxd Links

### Community 95 - "Config"
Cohesion: 0.18
Nodes (17): extract_cinemark_west_plano_dates(), parse_cinemark_west_plano_html(), The theatre page's own date-tab strip (`a.showdate-link     [data-datevalue="YYY, Parse one date's `GetByTheaterId` HTML fragment.      Each film gets one `div[cl, Fetch and parse one date's HTML per entry in `dates` (the site's     own date-ta, _walk_cinemark_west_plano_dates(), test_extract_cinemark_west_plano_dates_dedupes_and_preserves_order(), test_parse_cinemark_west_plano_html_badge_with_standard_text_tagged_by_badge() (+9 more)

### Community 96 - "Data Model: Tech Debt Cleanup — Cinema Routing, Deprecated APIs, Startup Coverage"
Cohesion: 0.12
Nodes (13): Cinema (existing — `src/cinema_recs/models.py`, `storage.py`), Data Model: Tech Debt Cleanup — Cinema Routing, Deprecated APIs, Startup Coverage, Migration, No new entities, State transitions, Build and run, Prerequisites, Quickstart: Tech Debt Cleanup — Cinema Routing, Deprecated APIs, Startup Coverage (+5 more)

### Community 97 - "web.py"
Cohesion: 0.38
Nodes (13): Evaluate every feature-002-matched movie against the configured     Letterboxd c, run_recommendation_evaluation(), _config(), _seed_matched_movie(), test_does_not_relookup_already_cached_letterboxd_data(), test_failed_watchlist_refresh_keeps_stale_cache(), test_movie_above_rating_threshold_is_recommended(), test_movie_below_rating_threshold_is_not_recommended() (+5 more)

### Community 98 - "main.py"
Cohesion: 0.16
Nodes (14): _cinemark_format_badge_text(), _extract_cinemark_group_format(), fetch_texas_theatre_html(), _parse_cinemark_ticket_url_showtime(), _parse_listing_time(), datetime, time, Badge alt text like "Cinemark XD" carries a "Cinemark " prefix not     present o (+6 more)

### Community 99 - "init_schema"
Cohesion: 0.22
Nodes (7): `GET /`, `GET /health`, Out of scope for this contract, Web View Contract, `GET /`, Out of scope for this contract, Web View Contract (updated by feature 010)

### Community 100 - "Cinema"
Cohesion: 0.40
Nodes (5): Cross-feature note (feature 003), Data Model: Movie Metadata Enrichment via TMDB, Enrichment Attempt, Movie Metadata, Relationships

### Community 101 - "_ensure_letterboxd_data_cached"
Cohesion: 0.50
Nodes (4): 2. Projection Format Extraction Logic, Alternatives Considered, Decision, Rationale

## Knowledge Gaps
- **792 isolated node(s):** `check-prerequisites.sh script`, `common.sh script`, `setup-plan.sh script`, `setup-tasks.sh script`, `docker-entrypoint.sh script` (+787 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `run_notifications()` connect `run_notifications` to `storage.py`, `run_enrichment`, `run_ingestion`?**
  _High betweenness centrality (0.007) - this node is a cross-community bridge._
- **Why does `run_ingestion()` connect `run_ingestion` to `storage.py`, `run_enrichment`, `main.py`, `scraper.py`?**
  _High betweenness centrality (0.007) - this node is a cross-community bridge._
- **Why does `load_config()` connect `run_notifications` to `storage.py`, `scraper.py`?**
  _High betweenness centrality (0.004) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `run_ingestion()` (e.g. with `scrape_angelika_dallas_showtimes()` and `scrape_cinemark_west_plano_showtimes()`) actually correct?**
  _`run_ingestion()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `check-prerequisites.sh script`, `common.sh script`, `setup-plan.sh script` to the rest of the system?**
  _792 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `storage.py` be split into smaller, more focused modules?**
  _Cohesion score 0.054901960784313725 - nodes in this community are weakly interconnected._
- **Should `run_enrichment` be split into smaller, more focused modules?**
  _Cohesion score 0.09351432880844646 - nodes in this community are weakly interconnected._