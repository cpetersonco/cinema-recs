# Interface Contract: CI/CD Pipeline & Version Endpoint

This feature has two external-facing interfaces: the GitHub Actions
workflow's contract with GHCR/Watchtower, and the `/health` endpoint's
extended contract with the operator.

## GitHub Actions workflow: `.github/workflows/deploy.yml`

**Trigger**: `push` to `main` only (spec Assumptions — matches this
repo's existing single-branch workflow; not triggered on pull requests
or other branches).

**Steps contract** (each step gates the next — spec FR-002/FR-007):

1. **Test**: install dependencies inside the Playwright base image
   (research.md), run `pytest` and `ruff check`. Any failure stops the
   workflow here — no image is built, no `docker/build-push-action`
   step runs, the currently published `latest` tag is untouched.
2. **Build**: on test success, `docker build` the existing `Dockerfile`
   for `linux/amd64`, passing `--build-arg GIT_SHA=<short commit sha>`.
3. **Push**: push two tags to `ghcr.io/cpetersonco/cinema-recs`:
   - `<short commit sha>` (immutable, one per successful build)
   - `latest` (always repointed to the newest successful build)

   Authentication uses the automatically-provided `GITHUB_TOKEN` via
   `docker/login-action` with `registry: ghcr.io` — no manually-created
   secret is required (research.md).

**Failure contract**: If any step fails, the workflow run is marked
failed in GitHub's UI (visible to the operator there), no new tag is
published, and Tower's currently-running container is unaffected
(spec SC-005 — zero downtime/degradation on a failed build).

## Watchtower ↔ GHCR ↔ `cinema-recs` container

**Watchtower's contract** (external tool, not code in this repo):
polls `ghcr.io/cpetersonco/cinema-recs:latest`'s digest on its
configured interval; when the digest differs from the currently running
container's image, it stops the old container, starts a new one from
the new image with the same name, env vars, volume mounts, port
mapping, and restart policy, and removes the old container/image
(standard Watchtower behavior — nothing in this repo needs to implement
this).

**This repo's contract with Watchtower**: `docker-compose.yml`'s
`cinema-recs` service carries the label
`com.centurylinklabs.watchtower.enable: "true"`, which is the only
coupling point — Watchtower is configured (on the Unraid side, per
quickstart.md) with `WATCHTOWER_LABEL_ENABLE=true` so it only acts on
labeled containers.

## `/health` endpoint (extended)

**Existing contract** (feature 001, unchanged): returns the latest
`IngestionRun`'s outcome/timing/error, per cinema.

**New contract** (this feature): also renders `APP_VERSION` (read from
the environment at request time, set from the `GIT_SHA` build arg — see
data-model.md). When the image was built without CI (a local `docker
build .` with no `--build-arg GIT_SHA=...`), this MUST render the
Dockerfile's documented default (`dev`) rather than an empty or broken
section — the app must never fail to serve `/health` because a version
string is absent, consistent with this project's existing "no broken
section for missing data" pattern (features 002/004).
