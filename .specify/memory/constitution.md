<!--
Sync Impact Report
Version change: 1.0.0 → 1.0.1
Modified principles: none
Added sections: none
Modified sections:
  - Development Workflow: documented the graphify knowledge graph and its
    .specify/extensions.yml hooks (before_plan, after_implement)
Removed sections: none
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no changes needed (Constitution Check section reads gates dynamically)
  - .specify/templates/spec-template.md ✅ no changes needed (no constitution-specific placeholders)
  - .specify/templates/tasks-template.md ✅ no changes needed (task categories remain generic)
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
  principle.
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

**Version**: 1.0.1 | **Ratified**: 2026-07-22 | **Last Amended**: 2026-07-22
