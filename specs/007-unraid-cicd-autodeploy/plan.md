# Implementation Plan: Automatic CI/CD Deployment to Unraid

**Branch**: `007-unraid-cicd-autodeploy` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-unraid-cicd-autodeploy/spec.md`

## Summary

Add a GitHub Actions workflow that, on every push to `main`, runs the
existing `pytest` suite and `ruff` lint, and — only if both pass — builds
a linux/amd64 Docker image tagged with both `latest` and the commit SHA,
and publishes it to GitHub Container Registry (GHCR) as a public image
(this repo is already public, so no registry credentials are needed on
the Tower side at all). On Tower, a single host-wide Watchtower instance
(installed once via Unraid's Community Applications store — not a
container this repo's `docker-compose.yml` owns) polls GHCR and
recreates the `cinema-recs` container whenever a new image is published,
preserving the existing `/data` volume mount. `docker-compose.yml` gains
one opt-in label so Watchtower only touches this container, not
unrelated ones on the host. The image records its own build SHA at
build time; `/health` is extended to display it so the operator can
confirm what's running without SSHing in (FR-008/SC-003).

## Technical Context

**Language/Version**: No new application language — CI is GitHub Actions
YAML + the existing Dockerfile; the app itself remains Python 3.11+

**Primary Dependencies**: `docker/build-push-action` and
`docker/login-action` (official GitHub Actions), GHCR (`ghcr.io`) as the
registry, Watchtower (`containrrr/watchtower`) as the only new runtime
component on Tower — no new Python dependency

**Storage**: N/A — no data model change; the existing SQLite `/data`
volume must survive container recreation, which Watchtower does natively
(it recreates a container with the same mounts/env/ports it replaces)

**Testing**: The project's existing `pytest` suite (`tests/unit/`,
`tests/integration/`) becomes the CI gate (spec FR-002); run inside the
same Playwright base image the Dockerfile already uses, since some
modules import `playwright` at module load time even though the unit
tests themselves mock network calls rather than launching a real browser

**Target Platform**: GitHub-hosted `ubuntu-latest` runner for CI/build;
linux/amd64 for the published image (Tower's Unraid host architecture —
single-arch build, no multi-arch needed for a single deploy target)

**Project Type**: Infrastructure addition to the existing single-project
Docker deployment — no new service, no split into multiple containers

**Performance Goals**: Build+test+publish completing well within
GitHub Actions' free-tier limits (a few minutes for this project's small
test suite); Tower reflecting a new image within Watchtower's poll
interval (target ≤15 minutes per SC-001)

**Constraints**: No inbound connections to Tower from GitHub or the
public internet (spec FR-005) — the update mechanism must be pull-based
from Tower's side, not a push initiated by GitHub Actions; must not
require restructuring the app into multiple services (spec FR-010)

**Scale/Scope**: One image, one container, one host, one operator — no
multi-environment (staging/prod) or multi-region concerns

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Python-First | GitHub Actions YAML and Watchtower are third-party CI/deployment tooling, explicitly exempted by the constitution's own "third-party services and tooling" carve-out; the only custom code added (version display on `/health`) is Python, consistent with the rest of the app | PASS |
| II. Docker-Native Deployment | Reinforces this principle directly — the app's existing single-image Docker packaging is unchanged; this feature only makes deploying that same image automatic | PASS |
| III. Unraid Runtime Compatibility | Watchtower is a standard, widely-used Unraid Community Applications template; `docker-compose.yml` still uses only env vars/volumes/ports, no new Unraid-incompatible assumptions | PASS |
| IV. Simplicity & Solo-Maintainer Ergonomics | Chose Watchtower (one well-known, purpose-built sidecar, zero new credentials since the image is public) over a self-hosted GitHub Actions runner on Tower (more moving parts, more attack surface, credentials living on the host) — see research.md for the full comparison | PASS |
| V. Observability for Self-Hosting | Watchtower logs every update it performs to its own container's stdout (visible via Unraid's log viewer, satisfying FR-009); GitHub Actions provides build/test logs for every push; `/health` now shows the running version so state is visible without SSH | PASS |

No violations identified; Complexity Tracking is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/007-unraid-cicd-autodeploy/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── contracts/             # Phase 1 output (/speckit-plan command)
└── tasks.md                # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
.github/
└── workflows/
    └── deploy.yml           # new: test (pytest+ruff) -> build -> push to ghcr.io on push to main

Dockerfile                   # extend: ARG GIT_SHA + ENV APP_VERSION, baked in at build time
docker-compose.yml           # extend: add a Watchtower opt-in label to the existing cinema-recs service (no new service definition — Watchtower itself is installed once via Unraid CA, outside this repo)

src/
└── cinema_recs/
    └── web.py                  # extend: /health displays APP_VERSION (commit SHA) alongside existing ingestion-run info

README.md                       # extend: document the CI/CD pipeline and the one-time Unraid-side Watchtower setup
```

**Structure Decision**: This feature adds exactly one new file
(`.github/workflows/deploy.yml`) and extends three existing files
(`Dockerfile`, `docker-compose.yml`, `web.py`) — no new service, package,
or directory structure. Watchtower itself is deliberately **not** added
as a service in this repo's `docker-compose.yml`: on Unraid, one
Watchtower instance is meant to watch the whole host, not be redeployed
per-app-stack, so it's installed once via Unraid's Community Applications
store (documented as a one-time setup step in quickstart.md) and scoped
to this container via a `com.centurylinklabs.watchtower.enable=true`
label on the `cinema-recs` service, keeping unrelated containers (e.g.
the `DUMB` media stack) unaffected (spec Assumptions).

## Complexity Tracking

*No violations — table intentionally omitted.*
