# Infrastructure

| File | Purpose | Exposure |
| --- | --- | --- |
| Root `docker-compose.yml` | Bind-mounted development stack | Development host ports |
| `compose.desktop.yml` | Installed single-PC platform built from the downloaded bundle | Frontend/API on loopback only |
| `compose.staging.yml` | Hardened locally built staging images | Configured staging origin |
| `compose.production.yml` | Immutable GHCR image deployment | Loopback behind separately managed HTTPS |

All layouts apply Alembic migrations before FastAPI starts. They do not create users or seed
dashboard records. On an empty database, the operator creates the initial administrator once in the
browser.

The Windows installer generates the desktop `.env` with independent PostgreSQL, JWT, and endpoint
sensor secrets. Do not share or commit it. Desktop PostgreSQL is private to the Compose network;
backend and frontend bind to `127.0.0.1`. The host sensor runs outside Docker because containers
cannot inspect Windows host event logs and processes.

Staging and production use ignored environment files derived from the matching examples. Replace
every placeholder, terminate remote access with HTTPS, keep PostgreSQL private, and take a verified
backup before migrations. See `docs/deployment.md` and `docs/endpoint-sensor.md`.
