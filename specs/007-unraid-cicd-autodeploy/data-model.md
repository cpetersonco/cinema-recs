# Data Model: Automatic CI/CD Deployment to Unraid

This feature introduces no application database tables or persisted
entities — it's a build/deploy pipeline, not a data feature. The two
"entities" named in spec.md's Key Entities are represented as follows,
neither requiring new storage:

## Container Image

Represents one successful build. Not stored in the application database
— it lives entirely in GHCR as a standard OCI image, identified by tags:

| Attribute | Representation |
|---|---|
| Identity | `ghcr.io/cpetersonco/cinema-recs` repository |
| Version tag | The short git commit SHA it was built from (e.g. `a1b2c3d`) |
| Latest pointer | The `latest` tag, always repointed to the most recent successful build on `main` |
| Traceability | The same SHA is baked into the image itself as `APP_VERSION` (research.md), so a running container can self-report which image tag it is, independent of the registry |

## Deployment/Update Event

Represents one Watchtower update attempt on Tower. Not stored in the
application database either — Watchtower emits its own log line per
check/update cycle to its container's stdout, which Unraid's existing
Docker log viewer already surfaces (Constitution V):

| Attribute | Representation |
|---|---|
| When | Watchtower's log timestamp |
| Outcome | Watchtower's own log message (no new image found / updated to `<tag>` / pull failed) |
| Which version it moved to | The new image tag Watchtower recreated the container with, visible in its log line and afterward via `/health`'s `APP_VERSION` |

No new SQLite tables, no new `cinema_recs.storage` module changes, and
no new Python dataclasses in `models.py` are needed for this feature.
