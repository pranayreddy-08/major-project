# Phase 8 progress record

## CI and image delivery

- Added direct-to-`main`, tag, and manual GitHub Actions triggers.
- Added independent backend, ML, frontend, and PostgreSQL migration lifecycle gates.
- Added gated GHCR publication for commit-, branch-, and release-tagged backend/frontend images.
- Pinned current major releases of the official GitHub setup and Docker build actions.

## Migration and runtime hardening

- Added Alembic environment and initial revision `bbfa5454db7e` for all 13 application tables.
- Replaced Compose `create_all` startup with migration-first startup.
- Separated production account bootstrap from staging-only synthetic dashboard seeding.
- Added multi-stage backend and frontend images, non-root UIDs, health checks, an unprivileged Nginx
  same-origin API proxy, security headers, read-only filesystems, dropped capabilities, and bounded
  container logs.

## Verification

- Validated migration upgrade, drift check, full downgrade, re-upgrade, and idempotent staging seed.
- Built both production images and ran the isolated three-service staging layout.
- Verified proxied authentication/dashboard API, CSP, health, non-root UIDs, read-only roots, and the
  exact Alembic head.
- Created and inspected a temporary PostgreSQL custom-format backup, then removed that test artifact.
- Added deployment, secret handling, backup/restore, rollback, and release-checklist documentation.

## Boundary

Repository delivery and local staging are complete. A public deployment is intentionally pending a
user-selected host/domain and explicit cloud/TLS/secret-store credentials; none are inferred or
committed by the project.
