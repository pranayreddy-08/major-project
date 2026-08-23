# Infrastructure

The root `docker-compose.yml` is the bind-mounted development environment. Phase 8 adds two separate
release layouts:

| File | Purpose | Data policy |
| --- | --- | --- |
| `compose.staging.yml` | Builds and runs the hardened images locally or on a staging host | Deterministic synthetic demo data only |
| `compose.production.yml` | Pulls immutable GHCR images and runs migrations/account bootstrap | No synthetic dashboard seed |

Copy the matching `.env.*.example` file to an ignored `.env.*` file and replace every placeholder.
Never commit the copied file. Production services bind to loopback; terminate HTTPS in a host-level
reverse proxy or managed load balancer before exposing the frontend.

Both layouts use named PostgreSQL volumes, health-gated startup, bounded local log rotation,
read-only application filesystems, dropped capabilities, and `no-new-privileges`. Backend startup
applies Alembic migrations before serving traffic. Detailed commands, backup/restore steps, and
rollback behavior are in `docs/deployment.md`.
