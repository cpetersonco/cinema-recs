# Quickstart: Automatic CI/CD Deployment to Unraid

## Prerequisites

- The `cpetersonco/cinema-recs` GitHub repository (already public — no
  new visibility change needed)
- Tower already running the `cinema-recs` container per its existing
  `docker-compose.yml` (features 001–006)
- Tower has outbound internet access (it already does, for scraping and
  the TMDB/Letterboxd/Discord calls)

## One-time setup

### 1. GitHub Actions (no secrets to create)

The workflow at `.github/workflows/deploy.yml` uses the automatically-
provided `GITHUB_TOKEN` to push to GHCR — no repository secrets need to
be added manually. Confirm the repo's **Settings → Actions → General →
Workflow permissions** allows "Read and write permissions" (required for
`GITHUB_TOKEN` to push packages).

### 2. Make the GHCR package public (one-time, after the first push)

After the workflow's first successful run publishes an image, go to the
package page at `https://github.com/users/cpetersonco/packages/container/package/cinema-recs`,
open **Package settings**, and change visibility to **Public**. This
only needs doing once — subsequent pushes to the same package stay
public.

### 3. Install Watchtower on Tower (via Unraid Community Applications)

1. In Unraid's **Apps** tab, search for "Watchtower" and install the
   `containrrr/watchtower` template.
2. Set its `WATCHTOWER_LABEL_ENABLE` environment variable to `true` (so
   it only touches labeled containers, not the whole host — research.md).
3. Set `WATCHTOWER_POLL_INTERVAL` to your preferred check frequency in
   seconds (e.g. `900` for 15 minutes, matching SC-001's target).
4. Start the container.

### 4. Redeploy `cinema-recs` with the updated `docker-compose.yml`

The `cinema-recs` service now includes the
`com.centurylinklabs.watchtower.enable: "true"` label. Run
`docker compose up -d` on Tower once to pick up this label (this is the
last manual redeploy this container should ever need).

## Validate it works

1. **Confirm CI runs on push**: push a trivial commit to `main` (or open
   the Actions tab after any real commit) and confirm the workflow runs
   test → build → push, ending with a new tag visible on the GHCR
   package page (spec FR-001/FR-003).

2. **Confirm a failing commit never publishes**: push a commit that
   intentionally breaks a test, confirm the workflow fails at the test
   step, and confirm no new tag appears on the GHCR package page
   (spec FR-002/FR-007, SC-002).

3. **Confirm automatic deployment end-to-end**: make a small, visible
   change (e.g., a label on the `/health` page), push to `main`, wait
   for the workflow to publish, then wait up to the configured
   Watchtower poll interval. Visit `http://<tower-ip>:8080/health` and
   confirm both the visible change and the updated `APP_VERSION` (short
   commit SHA) are present — with no manual action taken on Tower
   (spec US1, SC-001).

4. **Confirm data survives the update**: before triggering step 3,
   note the ingested showtimes visible on `/`. After the automatic
   update completes, confirm the same showtimes are still present (spec
   FR-006, SC-004).

5. **Confirm offline recovery**: stop the Watchtower container (or take
   Tower offline briefly), push a commit, wait, then start Watchtower
   (or bring Tower back) — confirm the update is applied on Watchtower's
   next poll rather than being missed (spec Edge Cases).

See [contracts/deploy-pipeline-interface.md](./contracts/deploy-pipeline-interface.md)
for the full workflow/registry/Watchtower contract, and
[data-model.md](./data-model.md) for how version/deployment state is
represented without any new database tables.
