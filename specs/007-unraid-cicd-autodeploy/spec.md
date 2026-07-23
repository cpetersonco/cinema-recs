# Feature Specification: Automatic CI/CD Deployment to Unraid

**Feature Branch**: `007-unraid-cicd-autodeploy`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Create a CI/CD plan for running this container on my local Unraid server. Investigate a way to automatically pull in new code changes based on Github commits, Github actions or otherwise."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ship a merged commit without manual deploy steps (Priority: P1)

As the operator, when I merge a commit to the main branch, I want the
container already running on my Unraid server to automatically update to
that new code, so I never have to SSH in, rebuild, or restart anything
by hand to see my changes live.

**Why this priority**: This is the entire point of the request — closing
the gap between "code merged" and "code running." Every other part of
this feature exists to make this safe and visible, not to replace it.

**Independent Test**: Can be fully tested by merging a small, visible
code change (e.g., a log message or listing-view label change) to main
and confirming, without any manual intervention, that the Unraid-hosted
container is running that change within the target window.

**Acceptance Scenarios**:

1. **Given** a commit is merged to main, **When** the automated pipeline
   finishes, **Then** the container running on the Unraid server is
   replaced with one built from that commit, with no manual step
   performed by the operator.
2. **Given** no new commit has been merged, **When** time passes,
   **Then** the running container's version does not change (no
   unnecessary restarts/redeploys).

---

### User Story 2 - Never auto-deploy a broken commit (Priority: P1)

As the operator, I want a commit that fails automated tests to never
reach the running container on Unraid, so a bad change can't take down
the service I depend on without my knowledge.

**Why this priority**: Automatic deployment without a quality gate turns
every push into a live production risk. This is what makes "automatic"
safe enough to actually want, not just fast.

**Independent Test**: Can be fully tested by merging a commit that
intentionally fails the test suite and confirming the previously running
(good) version keeps serving unchanged, with no partial or broken
deployment occurring.

**Acceptance Scenarios**:

1. **Given** a merged commit fails the automated test suite, **When**
   the pipeline runs, **Then** no new image is deployed and the
   currently running container is left untouched.
2. **Given** a merged commit passes the automated test suite, **When**
   the pipeline runs, **Then** the new image is built and made available
   for deployment.

---

### User Story 3 - Know what's actually running (Priority: P2)

As the operator, I want to be able to tell which commit or version is
currently running on my Unraid server, so I'm never left guessing
whether an update actually took effect.

**Why this priority**: Automatic deployment that operates silently
creates its own trust problem — the operator needs a way to verify the
pipeline is doing what it claims, even though this isn't required for
the update itself to work.

**Independent Test**: Can be fully tested by merging a commit, waiting
for deployment to complete, and confirming the operator can determine
the running version/commit without SSHing in and manually inspecting
file timestamps or image layers.

**Acceptance Scenarios**:

1. **Given** a new version has been deployed, **When** the operator
   checks, **Then** they can identify which commit is currently running.
2. **Given** the operator checks before any deployment has ever run,
   **When** they look, **Then** the absence of version information is
   itself informative (not a broken/empty page).

---

### Edge Cases

- What happens when the build or test stage fails partway through?
  Nothing already running is affected — the previous, working version
  continues to serve until a future commit passes.
- What happens when the Unraid server is powered off, offline, or
  otherwise unreachable at the moment a new commit is merged? The update
  must still apply automatically once the server is reachable again,
  without requiring the operator to notice and manually trigger it.
- What happens when two commits are merged in quick succession, before
  the first has finished deploying? The server should end up running the
  latest commit, not get stuck on or overwritten by an intermediate one.
- What happens to the application's persisted data (the showtime/
  recommendation database) across an automatic update? It must survive
  the update completely intact — an update is a code/image change, not a
  data reset.
- What happens if a newly deployed image starts but immediately crashes
  or fails health checks? This is called out explicitly in Assumptions
  as a known gap for this phase (no automatic rollback), since Tower has
  no existing automatic-rollback tooling for other containers either.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST automatically build a new deployable
  container image whenever a commit is merged to the main branch.
- **FR-002**: The system MUST run the project's existing automated test
  suite as part of that build, and MUST NOT make an image available for
  deployment when the tests fail for that commit.
- **FR-003**: The system MUST make a successfully-built image available
  for the Unraid server to retrieve, without requiring the operator to
  manually transfer or copy it.
- **FR-004**: The system MUST update the running container on the
  Unraid server to a newly available image automatically, within a
  bounded and predictable amount of time after the image becomes
  available, without the operator manually SSHing in or issuing
  commands.
- **FR-005**: The system MUST NOT require the Unraid server to accept
  inbound network connections from the public internet as part of this
  mechanism — the server is reachable only via the operator's private
  network/VPN, not the open internet.
- **FR-006**: The update mechanism MUST preserve the container's
  persistent data volume (the application database and any other
  mounted state) across every automatic update.
- **FR-007**: The system MUST leave the currently running container
  unchanged and continuing to serve whenever the build or test stage
  fails for a newer commit.
- **FR-008**: The system MUST allow the operator to determine which
  commit or version is currently running on the Unraid server without
  SSHing in and manually inspecting the container or its files.
- **FR-009**: The system MUST log or otherwise record deployment/update
  attempts (both successful and failed) so the operator can review when
  updates occurred, consistent with this project's existing practice of
  surfacing operational events rather than failing silently.
- **FR-010**: The system MUST continue to work with the project's
  existing single-container Docker deployment model — it MUST NOT
  require splitting the application into multiple services or changing
  how the application itself is packaged.

### Key Entities

- **Container Image**: The versioned, immutable build artifact produced
  from a specific commit. Each successful build produces exactly one
  image, traceable back to the commit it was built from.
- **Deployment/Update Event**: A record of one attempt to bring the
  Unraid server's running container in line with the latest available
  image — attributes include when it happened, which version it moved
  to (or attempted to move to), and whether it succeeded.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A commit merged to main results in the Unraid-hosted
  container running that commit's code within 15 minutes, with zero
  manual steps performed by the operator.
- **SC-002**: 100% of commits that fail the automated test suite never
  reach the running container on the Unraid server.
- **SC-003**: The operator can identify the currently running commit/
  version within one minute of checking, without SSHing into the
  server.
- **SC-004**: Persisted application data (ingested showtimes,
  recommendation/notification history) survives 100% of automatic
  updates with zero data loss.
- **SC-005**: An update that fails to build or fails tests results in
  zero downtime or degradation of the currently running service.

## Assumptions

- "Automatically pull in new code changes" means: on every commit
  merged to the `main` branch (this project's existing single working
  branch, per its git history), not on every push to an arbitrary
  branch or pull request — matching how this repository has been used
  so far.
- The Unraid server (Tower) is reachable only over the operator's
  private network/VPN, not the public internet, and has no inbound port
  forwarded to it from GitHub or any public CI service. This rules out
  a design where GitHub-hosted infrastructure directly connects into
  Tower to push an update; the update must instead be something Tower
  (or an agent with access to it) initiates or polls for. This is the
  reason FR-005 exists as an explicit requirement rather than an
  incidental detail.
- A container registry reachable by both the build pipeline (to publish
  images) and the Unraid server (to retrieve them) is an acceptable and
  expected part of the solution — this is standard practice for
  container-based deployment and is not itself a scope concern.
- No automatic rollback is in scope for this phase: if a newly deployed
  image is unhealthy, restoring the previous known-good version is a
  manual operator action, consistent with how the operator currently
  handles other container issues on Tower (per existing incident
  history, problems are diagnosed and fixed manually, not
  auto-remediated).
- Secrets and environment-specific configuration (API keys, webhook
  URLs, etc.) are already managed on the Unraid server today (via
  environment variables per this project's existing deployment docs)
  and continue to be managed there — this feature automates *code/image*
  delivery, not configuration/secret provisioning.
- The 15-minute target in SC-001 reflects a periodic check on the
  Unraid side rather than an instant push notification, since Tower
  cannot be pushed to directly (see above); this interval is expected to
  be operator-configurable rather than fixed.
- This feature covers the `cinema-recs` container only; it does not
  extend to other containers or services running on Tower (e.g., the
  unrelated `DUMB` media stack).
