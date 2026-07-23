# Research: Automatic CI/CD Deployment to Unraid

No `NEEDS CLARIFICATION` markers remained in Technical Context — the
open questions here are technology-choice research, not scope
ambiguity.

## Decision: Pull-based update via Watchtower polling GHCR, not a push from GitHub Actions

**Decision**: Tower runs Watchtower, which polls GitHub Container
Registry on an interval and recreates the `cinema-recs` container when a
newer image is found. GitHub Actions never connects to Tower directly.

**Rationale**: Per the spec's FR-005 and Assumptions, Tower has no
inbound path from the public internet — it's reachable only via the
operator's private network/Tailscale. Any design where GitHub Actions
initiates a connection *into* Tower (SSH deploy, webhook receiver, etc.)
would require either exposing a port on the home network or joining a
GitHub-hosted runner to the operator's Tailscale network for every run.
A pull-based design sidesteps this entirely: Tower already has outbound
internet access (it pulls Docker images today), so polling GHCR requires
no new inbound exposure and no VPN-in-CI complexity.

**Alternatives considered**:
- *GitHub Actions SSHes into Tower and runs `docker compose pull && up
  -d` directly*: rejected. Requires either a port-forward to Tower (ruled
  out by FR-005) or the GitHub-hosted runner joining the operator's
  Tailscale network per run (via the `tailscale/github-action`), which
  adds a Tailscale auth key as a long-lived GitHub secret, ACL
  configuration, and a new dependency on Tailscale's own service being
  reachable from GitHub's runners — meaningfully more moving parts for a
  single-container personal project (Constitution IV).
- *A self-hosted GitHub Actions runner installed on Tower itself*:
  rejected for the same reason as above, but worse — it gives arbitrary
  CI-triggered code (including from GitHub Actions' own supply chain)
  local Docker execution rights on Tower permanently, not just during a
  deploy. Watchtower's blast radius is limited to "recreate containers
  when a newer image exists," a much narrower capability.
- *Unraid's own built-in Docker "check for updates" notification*:
  rejected as the *sole* mechanism — it exists today but is a manual
  "click to update" UI action, not automatic, so it doesn't satisfy
  FR-004 ("without the operator manually SSHing in or issuing
  commands"). Watchtower is the standard automation layer on top of the
  same underlying Docker pull mechanism Unraid's UI uses.

## Decision: Publish images to GHCR as public (repo is already public)

**Decision**: Push images to `ghcr.io/cpetersonco/cinema-recs` and mark
the package public, so Watchtower on Tower can pull without any registry
credentials configured on the host.

**Rationale**: The `cpetersonco/cinema-recs` GitHub repository is
already public (verified via the GitHub API). GHCR lets a public repo's
published packages be made public too, at which point `docker pull`
requires no authentication at all. This means zero new secrets need to
live on Tower — Watchtower just needs outbound internet access, which it
already has. Publishing from GitHub Actions itself uses the built-in,
automatically-scoped `GITHUB_TOKEN` (via `docker/login-action` with
`registry: ghcr.io`), not a manually-created personal access token.

**Alternatives considered**:
- *Docker Hub*: rejected — would work equally well technically, but
  GHCR requires no separate account/credential setup since it's already
  tied to the same GitHub repo and its built-in token; no reason to add
  a second external account for a single-image project.
- *Private GHCR package + a pull secret configured on Tower*: rejected
  as unnecessary complexity — this is not a sensitive image (no secrets
  are baked into it; all secrets are supplied at runtime via env vars
  per the project's existing config pattern), so there's no security
  reason to keep it private, and doing so would require provisioning and
  rotating a registry credential on Tower for no real benefit.

## Decision: Test suite runs inside the same Playwright base image as production

**Decision**: The CI job's test step uses
`mcr.microsoft.com/playwright/python:v1.48.0-jammy` (the same base image
the Dockerfile already builds from) rather than a bare `ubuntu-latest` +
`pip install`.

**Rationale**: `src/cinema_recs/scraper.py` imports
`playwright.sync_api` at module load time, so any test file that
imports from `scraper.py` (directly or transitively via `ingest.py`)
fails to collect at all without Playwright installed — confirmed
locally during this session's `/speckit-converge` runs, where those
test files errored out with `ModuleNotFoundError` until Playwright was
installed in the ad-hoc verification environment. None of the current
unit tests launch a real browser (they mock the scrape functions), but
the import must still succeed. Using the same base image as production
avoids a second, drifting definition of "what Python/Playwright version
this project runs on."

**Alternatives considered**:
- *Install bare `playwright` + `playwright install --with-deps
  chromium` on a plain `ubuntu-latest` runner*: rejected as unnecessary
  extra CI time (browser binary download) for zero benefit, since no
  test actually launches a browser today; if that changes later, this
  decision should be revisited.
- *Mark Playwright-dependent test modules as CI-skipped*: rejected —
  would let a broken import in `scraper.py` or `ingest.py` slip past CI
  silently, directly undermining spec FR-002's "must not deploy a commit
  that fails tests" guarantee.

## Decision: Version visibility via a build-time `GIT_SHA` baked into the image, surfaced on `/health`

**Decision**: The GitHub Actions build step passes `--build-arg
GIT_SHA=$(git rev-parse --short HEAD)` (or `${{ github.sha }}`,
shortened) to `docker build`; the Dockerfile declares `ARG GIT_SHA=dev`
and `ENV APP_VERSION=$GIT_SHA`. `web.py`'s existing `/health` route reads
`APP_VERSION` from the environment and displays it.

**Rationale**: Satisfies FR-008/SC-003 ("operator can identify the
running version without SSHing in") using the project's existing
Flask app and its existing `/health` page — no new endpoint, no new
service, no external version-tracking system. Defaulting `ARG
GIT_SHA=dev` means a local `docker build .` (no CI) still produces a
working image that clearly reports itself as a dev build rather than
silently claiming a stale or blank version.

**Alternatives considered**:
- *Tag-only versioning (rely on `docker inspect` image digest via SSH)*:
  rejected — this is exactly the manual SSH step FR-008 exists to
  eliminate.
- *A dedicated `/version` JSON endpoint*: considered reasonable, but
  extending the existing `/health` page (already the project's
  operational-status surface, per feature 001) is simpler than adding a
  second endpoint for a single string value (Constitution IV).

## Decision: Watchtower scoped via container label, not blanket host-wide auto-update

**Decision**: Watchtower is installed once on Tower (outside this repo,
via Unraid's Community Applications store) configured with
`WATCHTOWER_LABEL_ENABLE=true`, and `docker-compose.yml`'s
`cinema-recs` service gets the label
`com.centurylinklabs.watchtower.enable: "true"`.

**Rationale**: Without label-scoping, a single Watchtower instance would
attempt to auto-update *every* container on Tower, including the
unrelated `DUMB` media stack and its sub-containers — well outside this
feature's scope (spec Assumptions explicitly excludes them) and a
meaningfully higher-risk change than what was asked for. Label-scoping
keeps the blast radius to exactly the one container this feature is
about, while still allowing the operator to opt other containers in
later through the same mechanism if they choose to.

**Alternatives considered**:
- *A second, project-dedicated Watchtower container defined in this
  repo's own `docker-compose.yml`*: rejected — running multiple
  Watchtower instances on one host is redundant (each would poll
  independently) and fights against Unraid's convention of one
  host-wide instance managed through its own UI; also would make this
  repo's compose file responsible for infra (Watchtower's own update
  cadence/config) that has nothing to do with the cinema-recs app
  itself.
