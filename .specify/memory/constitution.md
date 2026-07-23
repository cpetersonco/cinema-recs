<!--
Sync Impact Report
Version change: 1.0.1 → 1.1.0
Modified principles: none (existing I-V unchanged)
Added sections:
  - Core Principles VI. Explicit Over Inferred
  - Core Principles VII. Live-Verify External Integrations
  - Core Principles VIII. Network-Isolated Automated Tests
  - Core Principles IX. Backward-Compatible Schema Migrations
Modified sections: none
Removed sections: none
Rationale for MINOR bump: four new principles added, each codifying a
pattern that recurred across multiple shipped features (001/006/008/009
live-verification; 001/005/011 idempotent migrations; the whole test
suite's network-mocking convention; the routing bug just fixed in 011) —
not new restrictions invented in the abstract, but existing practice made
explicit so it doesn't erode as the project grows.
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no changes needed (Constitution Check section reads gates dynamically)
  - .specify/templates/spec-template.md ✅ no changes needed (no constitution-specific placeholders)
  - .specify/templates/tasks-template.md ✅ no changes needed (task categories remain generic)
  - README.md ✅ checked, no constitution/principle references present
Follow-up TODOs: none
-->

# Cinema Recs Constitution

## Core Principles

### I. Python-First
All application code MUST be written in Python. Third-party services and
tooling (e.g., databases, reverse proxies) are exempt, but any custom logic,
scripts, or integrations built for this project MUST be implemented in
Python rather than introducing a second application language.

**Rationale**: This is a single-maintainer personal project. Standardizing
on one language keeps the codebase approachable to maintain without context
switching between runtimes.

### II. Docker-Native Deployment
The application MUST be packaged and runnable as a Docker container.
A `Dockerfile` (and, where useful, a `docker-compose.yml`) MUST be kept
up to date and buildable from a clean checkout. Features MUST NOT depend
on host-level installation steps that cannot be expressed inside the
container image or its declared volumes/environment variables.

**Rationale**: Docker is the deployment target for this project; anything
that can't be containerized can't be run in production for this user.

### III. Unraid Runtime Compatibility
The container MUST run correctly under Unraid's Docker runtime: it MUST
support configurable host volume mounts for persistent data, MUST accept
configuration via environment variables (not interactive prompts or
mandatory config-file edits inside the running container), and MUST NOT
assume a specific host UID/GID beyond what can be set via standard
`PUID`/`PGID`-style environment variables. Ports the app listens on MUST be
configurable rather than hardcoded where Unraid's UI would need to map them.

**Rationale**: Unraid manages containers through its own UI conventions
(volume mappings, env vars, port mappings). Following these conventions is
what makes the app installable and maintainable on the target server.

### IV. Simplicity & Solo-Maintainer Ergonomics
Prefer the simplest design that solves the current, real requirement.
Avoid speculative abstractions, plugin systems, or multi-service
architectures unless a concrete need exists today. New dependencies MUST
be justified by clear necessity, not convenience for hypothetical future
features.

**Rationale**: This is a personal project maintained by one person in
spare time; low cognitive overhead and low operational burden matter more
than enterprise-grade extensibility.

### V. Observability for Self-Hosting
The application MUST emit clear, readable logs to stdout/stderr (so Docker
and Unraid's log viewer can capture them) covering startup, errors, and key
operational events. Failures MUST produce actionable log messages rather
than silent failures, since there is no dedicated ops team to page.

**Rationale**: When something breaks on a home server, logs are the
primary — often only — debugging tool available.

### VI. Explicit Over Inferred
Any decision about which code path handles a piece of data (e.g., which
scraper a cinema's showtimes come from, which handler processes a given
record) MUST be set explicitly at the point the data is created or
configured, never inferred by pattern-matching names, URLs, or other
incidental text at use time. When a value doesn't match any explicitly
known case, the system MUST fail clearly and immediately rather than
silently falling back to a default or a best guess.

**Rationale**: A prior design inferred which cinema scraper to run by
substring-matching a cinema's name/URL, with an unrecognized source
silently falling back to the wrong scraper instead of failing (fixed in
feature 011). Explicit, closed-set state set once at creation time is
cheap to add and prevents this entire class of silent misrouting bug from
recurring as new sources/handlers are added.

### VII. Live-Verify External Integrations
Any feature whose behavior depends on an undocumented third-party site's
structure (scraper markup, API response shape, endpoint parameters) MUST
have that structure confirmed by inspecting the live site during planning
or implementation — not assumed from prior knowledge, general web
conventions, or documentation that doesn't exist for the target site.
The specific finding and how it was confirmed MUST be recorded (e.g., in
the feature's `research.md`).

**Rationale**: Every cinema-source feature shipped so far (001, 006, 008,
009) depends on sites with no public API and no stable documentation.
Feature 009 specifically planned Angelika Dallas's data source on an
assumption that live verification later proved wrong, requiring a
mid-implementation correction — live verification is not optional
diligence for this project, it's the only reliable source of truth for
integrations like these.

### VIII. Network-Isolated Automated Tests
Automated tests (unit and integration) MUST NOT make real network calls
to external services — cinema sources, TMDB, Letterboxd, Discord, or any
other third party. External calls MUST be mocked at the client-function
boundary. Validating real, live behavior against an external service is
done separately, manually, via a feature's `quickstart.md` steps — never
as part of the automated suite that runs on every change.

**Rationale**: This is already the convention followed by every test file
in the project (scraper tests use canned fixtures; ingestion/notification/
recommendation tests mock their respective clients). Writing it down
keeps the automated suite fast, deterministic, and runnable offline as
the project grows, rather than eroding one convenient real-network test
at a time.

### IX. Backward-Compatible Schema Migrations
Database schema changes MUST be additive and idempotent: implemented as a
migration function that checks for the change's absence (e.g., via
`PRAGMA table_info`) before applying it, applied automatically every time
the application starts, requiring no manual operator action and no
downtime. Destructive schema changes (dropping/renaming columns or
tables in a way that discards data) MUST NOT be used without an explicit,
separately-justified exception.

**Rationale**: This exact pattern has already been used three times
(showtime ticket URLs, notification disappearance tracking, cinema
source types) to evolve the single SQLite file this app persists to a
mounted volume — an existing deployment's database MUST keep working
across an upgrade with zero manual steps, since there is no ops team to
run a migration script by hand.

## Technology Constraints

- **Language**: Python (version choice and pinning tracked in the project's
  dependency files, e.g. `pyproject.toml` or `requirements.txt`).
- **Packaging/Deployment**: Docker image as the sole supported deployment
  artifact; must build and run standalone via `docker run` or
  `docker compose up` without additional undocumented setup steps.
- **Target host**: Unraid server (Docker runtime). Features and
  configuration MUST be validated against Unraid's volume-mount and
  environment-variable conventions before being considered done.
- **Data persistence**: Any state that must survive container restarts
  MUST be written to a path intended for a mounted volume, not baked into
  the image or left in ephemeral container storage.

## Development Workflow

- Changes are developed and reviewed by a single maintainer; formal PR
  review gates are not required, but each change SHOULD be validated by
  running the container locally (or via the project's test suite, where
  one exists) before being considered done.
- New features that affect how the container is configured or run
  (new env vars, new ports, new volumes) MUST update any deployment
  documentation (e.g., README, docker-compose.yml) in the same change.
- Automated tests are encouraged for logic with real failure risk
  (parsing, recommendation logic, external API integration) but are not
  mandatory for trivial glue code, consistent with the Simplicity
  principle. Where tests do touch external services, they follow
  Principle VIII (Network-Isolated Automated Tests).
- The repo maintains a `graphify` knowledge graph (`graphify-out/`, gitignored
  and rebuilt locally) for architecture/dependency navigation. Spec Kit hooks
  registered in `.specify/extensions.yml` consult it before planning
  (`before_plan`) and refresh it after implementation (`after_implement`,
  no API cost via `graphify update .`).

## Governance

This constitution supersedes ad-hoc practices for this project. Amendments
require updating this file directly (via `/speckit-constitution` or manual
edit), incrementing the version per semantic versioning rules below, and
recording the change in the Sync Impact Report comment at the top of this
file:

- **MAJOR**: Backward-incompatible removal or redefinition of a principle.
- **MINOR**: A new principle or materially expanded section is added.
- **PATCH**: Wording clarifications or non-semantic fixes.

Any plan, spec, or task produced by the Spec Kit workflow MUST be checked
against these principles (see each template's "Constitution Check" or
equivalent section); deviations must be explicitly justified or the
approach revised.

**Version**: 1.1.0 | **Ratified**: 2026-07-22 | **Last Amended**: 2026-07-23
