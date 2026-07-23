---

description: "Task list for Automatic CI/CD Deployment to Unraid"

---

# Tasks: Automatic CI/CD Deployment to Unraid

**Input**: Design documents from `/specs/007-unraid-cicd-autodeploy/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/deploy-pipeline-interface.md, quickstart.md

**Tests**: A lightweight test is included for the one piece of new application logic (`/health`'s version display), consistent with this project's precedent of testing route/logic changes in `tests/integration/test_web_view.py`. The CI workflow itself has no unit-test surface — it's validated by the runnable scenarios in quickstart.md, not pytest.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Extends the existing single project at the repository root: `Dockerfile`, `docker-compose.yml`, `src/cinema_recs/`, `tests/`, plus one new `.github/workflows/` directory.

---

## Phase 1: Foundational (Blocking Prerequisites)

**Purpose**: Give the image a way to carry a build-time version, and give Watchtower a way to know which container it's allowed to touch — both required before the CI workflow (US1) or Watchtower (documented in quickstart.md) can do anything useful.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T001 Add `ARG GIT_SHA=dev` and `ENV APP_VERSION=$GIT_SHA` to `Dockerfile`, placed alongside the existing `ENV` block so a plain `docker build .` (no build-arg) still produces a working image reporting itself as `dev` (research.md's version-visibility decision)
- [X] T002 [P] Add the label `com.centurylinklabs.watchtower.enable: "true"` to the `cinema-recs` service in `docker-compose.yml`, scoping Watchtower's auto-update to only this container (research.md's label-scoping decision; plan.md's Structure Decision)

**Checkpoint**: Foundation ready — the image can self-report a version, and is opted in to Watchtower's label-based scoping

---

## Phase 2: User Story 1 - Ship a merged commit without manual deploy steps (Priority: P1) 🎯 MVP

**Goal**: A push to `main` automatically builds a `linux/amd64` image and publishes it to GHCR, tagged `latest` and with the commit's short SHA, with no manual step.

**Independent Test**: Push a trivial commit to `main`, confirm the GitHub Actions workflow runs to completion, and confirm a new image tag appears on the `ghcr.io/cpetersonco/cinema-recs` package page (quickstart.md step 1).

### Implementation for User Story 1

- [X] T003 [US1] Create `.github/workflows/deploy.yml`: trigger on `push` to `main`; a single job that checks out the repo, logs in to `ghcr.io` via `docker/login-action` using the built-in `GITHUB_TOKEN`, computes a short commit SHA, and uses `docker/build-push-action` to build the existing `Dockerfile` for `linux/amd64` with `--build-arg GIT_SHA=<short-sha>` and push both the `latest` and `<short-sha>` tags to `ghcr.io/cpetersonco/cinema-recs` (per contracts/deploy-pipeline-interface.md's workflow contract; depends on T001 for the build-arg to have somewhere to go)

**Checkpoint**: User Story 1 is fully functional and testable independently — every push to `main` now publishes a new image (quickstart.md step 1; note the GHCR package must be made public per quickstart.md's one-time setup before Watchtower can pull without credentials)

---

## Phase 3: User Story 2 - Never auto-deploy a broken commit (Priority: P1)

**Goal**: A commit whose tests fail never gets built into an image or published — the workflow stops before the build/push steps.

**Independent Test**: Push a commit that intentionally breaks a test, confirm the workflow fails at the test step, and confirm no new tag appears on the GHCR package page while the previously published `latest` tag is untouched (quickstart.md step 2).

### Implementation for User Story 2

- [X] T004 [US2] Extend the job in `.github/workflows/deploy.yml` (T003) with test/lint steps inserted *before* the login/build/push steps: install dependencies inside the `mcr.microsoft.com/playwright/python:v1.48.0-jammy` base image (research.md's test-environment decision — matches the Dockerfile's own base image so `playwright`-importing modules collect successfully), then run `pytest` and `ruff check`. Because GitHub Actions steps within a job run sequentially and a failing step stops the job by default, this requires no extra `if:`/`needs:` conditionals — a test/lint failure simply never reaches the later steps (depends on T003)

**Checkpoint**: User Stories 1 AND 2 both work independently — the pipeline both publishes on success and never publishes on failure (quickstart.md steps 1-2)

---

## Phase 4: User Story 3 - Know what's actually running (Priority: P2)

**Goal**: The operator can see which commit/version is currently running on Tower via the existing `/health` page, without SSHing in.

**Independent Test**: Build the image with `GIT_SHA` set and confirm `/health` displays it; separately, build without setting `GIT_SHA` and confirm `/health` displays `dev` rather than a broken or empty section (quickstart.md step 3; contracts/deploy-pipeline-interface.md's `/health` contract).

### Tests for User Story 3

- [X] T005 [P] [US3] Integration test in `tests/integration/test_web_view.py`: `GET /health` includes the value of the `APP_VERSION` environment variable when set (e.g. via `monkeypatch.setenv`), and includes the literal string `dev` when `APP_VERSION` is unset — mirroring the existing tests in that file for other `/health` fields

### Implementation for User Story 3

- [X] T006 [US3] Extend `HEALTH_TEMPLATE` and the `health()` route in `src/cinema_recs/web.py` to read `APP_VERSION` from the environment (default `"dev"`) and render it alongside the existing per-cinema ingestion-run sections (depends on T001 for the env var to be populated in a real deployment, and T005 for the test to already exist per this project's light-TDD precedent)

**Checkpoint**: All three user stories independently functional — publish, gate, and version-visibility all work (quickstart.md steps 1-4)

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and end-to-end validation

- [X] T007 [P] Update `README.md` with a new section documenting the CI/CD pipeline (what triggers it, where images are published) and linking to quickstart.md's one-time Unraid/Watchtower setup steps (GitHub Actions permissions, making the GHCR package public, installing/configuring Watchtower, redeploying once to pick up the new label)
- [X] T008 Local-equivalent validation completed in the implementation sandbox (no GitHub push or live Tower access available there): `docker build` succeeds both with and without `--build-arg GIT_SHA=...`, producing `APP_VERSION=<sha>` and `APP_VERSION=dev` respectively; `docker compose config` validates the updated `docker-compose.yml` (image/label present); full `pytest` suite (110/110) and `ruff check` on all changed files pass. Quickstart.md's 5 live scenarios (real push, real Watchtower poll on Tower, offline-recovery) still require running against the real GitHub repo and Tower after this is merged and pushed — flagged to the operator as the remaining manual verification step, not silently assumed complete

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 1)**: No dependencies — can start immediately; BLOCKS all user stories
- **User Story 1 (Phase 2)**: Depends on Foundational completion (T001, for the build-arg)
- **User Story 2 (Phase 3)**: Depends on Foundational completion; extends US1's workflow file (T003) with test/lint steps — same file, sequential extension, not a new file
- **User Story 3 (Phase 4)**: Depends on Foundational completion (T001); independent of US1/US2's workflow file — touches `web.py` instead
- **Polish (Phase 5)**: Depends on all three user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories — the MVP (publish on push)
- **User Story 2 (P1)**: Builds directly on US1's workflow file (T003) — adds the test/lint gate to the same job
- **User Story 3 (P2)**: Independent of US1/US2 — only depends on the Foundational Dockerfile change (T001), can be built in parallel with US1/US2

### Parallel Opportunities

- T001 and T002 (Foundational) can run in parallel — different files
- T005 (US3 test) can be written in parallel with T003/T004 (US1/US2, different files)
- T007 (Polish, README) can run in parallel with T008 (Polish, validation) once all user stories are done

---

## Parallel Example: Foundational Phase

```bash
# Launch independent foundational tasks together:
Task: "Add ARG GIT_SHA / ENV APP_VERSION to Dockerfile"
Task: "Add Watchtower opt-in label to docker-compose.yml"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Foundational
2. Complete Phase 2: User Story 1 (publish on push)
3. **STOP and VALIDATE**: Push a commit, confirm an image is published to GHCR
4. Deploy/demo if ready — note this alone doesn't yet gate on tests (US2) or expose version (US3)

### Incremental Delivery

1. Complete Foundational → image can self-version, container opted into Watchtower
2. Add User Story 1 → Validate publishing independently → the pipeline exists
3. Add User Story 2 → Validate the failing-commit gate independently → the pipeline is now safe to leave fully automatic
4. Add User Story 3 → Validate version visibility independently → the operator can trust and verify what's running
5. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Watchtower itself is not created by any task here — it's a one-time, Unraid-side manual setup step documented in quickstart.md, not application code (plan.md's Structure Decision)
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
