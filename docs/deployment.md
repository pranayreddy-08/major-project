# Phase 8 deployment guide

## Delivery model

`.github/workflows/ci.yml` runs on direct pushes to `main`, version tags matching `v*`, and manual
dispatch. Four independent gates validate backend, ML, frontend, and the Alembic migration lifecycle.
The container matrix runs only after every gate passes. Push events publish:

- `ghcr.io/pranayreddy-08/major-project-backend`;
- `ghcr.io/pranayreddy-08/major-project-frontend`.

Images receive a commit tag such as `sha-abc1234`, a branch/release tag, and `latest` for `main`.
Deployment must use the immutable `sha-*` tag recorded in the release notes, never rely on `latest`.
The workflow uses read-only repository permission except for the image job's scoped
`packages: write` permission and authenticates to GHCR with the repository `GITHUB_TOKEN`.

## Installed Windows deployment

Build `release\ecti-windows-x64.zip` on Windows with
`installer\windows\Build-Bundle.ps1`. After extracting it, run
`installer\windows\Install-ECTI.ps1`. The installer generates local secrets, builds the
loopback-only services, starts the current-user sensor, and opens <http://127.0.0.1:8080>. Create
the first owner in the browser. Use the adjacent `Start-ECTI.ps1` and `Stop-ECTI.ps1` scripts
afterward. Docker Desktop is required.

The installer does not create a Windows service, scheduled task, firewall rule, or public listener.
See `endpoint-sensor.md` for its telemetry and privilege boundary.

## Local staging deployment

Staging validates the hardened web-service layout. It starts with an empty account table.

```powershell
Copy-Item infra\.env.staging.example infra\.env.staging
# Replace all placeholder passwords/secrets in the ignored copy.
docker compose --env-file infra\.env.staging -f infra\compose.staging.yml config --quiet
docker compose --env-file infra\.env.staging -f infra\compose.staging.yml up --build -d
docker compose --env-file infra\.env.staging -f infra\compose.staging.yml ps
```

Open the configured `FRONTEND_ORIGIN`. Nginx serves the compiled SPA and proxies `/api/` to
FastAPI, so the browser never resolves an internal Docker hostname. The backend runs migrations
before accepting traffic; create the first owner through the setup screen.

## Production host prerequisites

1. A Linux host or container service with Docker Compose, persistent storage, outbound GHCR access,
   DNS, and an HTTPS reverse proxy/load balancer.
2. A deployment identity that can pull the private GHCR packages. Do not reuse a personal password;
   use the host/platform secret manager and the minimum package-read scope.
3. An encrypted PostgreSQL backup destination outside the application host.
4. Monitoring for `/health`, container restarts, disk/volume usage, HTTP 5xx/429 rates, migration
   failures, and authentication/audit anomalies.
5. A tested immutable backend/frontend image pair from the same commit SHA.

Copy `infra/.env.production.example` to an ignored protected file and supply real values from the
secret manager. `FRONTEND_ORIGIN` must be the public HTTPS origin. The example production Compose
binds frontend/backend ports to `127.0.0.1`; the external HTTPS proxy connects to the frontend only.
PostgreSQL has no host port.

## Backup, migration, and deployment

Resolve the exact project and environment file once:

```bash
ECTI_COMPOSE=(docker compose --env-file infra/.env.production -f infra/compose.production.yml)
```

Create a timestamped custom-format backup before changing images or schema:

```bash
"${ECTI_COMPOSE[@]}" exec -T postgres sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "ecti-before-release.dump"
pg_restore --list ecti-before-release.dump >/dev/null
```

Pull and start the exact SHA-tagged images from the environment file:

```bash
"${ECTI_COMPOSE[@]}" config --quiet
"${ECTI_COMPOSE[@]}" pull
"${ECTI_COMPOSE[@]}" up -d
"${ECTI_COMPOSE[@]}" ps
curl --fail --silent http://127.0.0.1:${FRONTEND_PORT:-8080}/health
```

Backend startup executes `alembic upgrade head` before the API. It does not create any account or
dashboard record. Create the first owner once through the setup screen and protect that endpoint by
keeping the service private until initialization is complete.

## Rollback

1. Stop new writes or place the service in maintenance mode.
2. Inspect `alembic current` and the failed release logs.
3. If the schema is backward compatible, restore the previous backend/frontend SHA tags and run
   `docker compose up -d`.
4. If the schema is not backward compatible, restore the verified pre-release backup into a new
   database/volume and point the previous application images at it. Prefer restore-forward over an
   unreviewed destructive downgrade.
5. Verify login, overview, graph, audit, and health before reopening traffic.
6. Retain the failed logs and record the incident; do not delete the old database until recovery is
   independently confirmed.

`alembic downgrade` is exercised on an empty CI database to prove revision mechanics. That does not
guarantee a data-preserving production downgrade after writes, which is why backup restore is the
authoritative rollback path.

## Current boundary

No remote host, DNS name, TLS certificate, cloud account, or secret store has been authorized in
this repository. Phase 8 therefore completes the tested CI/image/migration/staging/release package,
while the first external deployment requires the operator to choose a target and provide those
credentials explicitly.
