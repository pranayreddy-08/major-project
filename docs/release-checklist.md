# Release checklist

Record the commit SHA, image digests, operator, timestamp, environment, backup location, and rollback
image tags in the release notes. Do not continue when any required item fails.

## Before deployment

- [ ] Backend, ML, frontend, sensor, migration, and container jobs passed for the same SHA.
- [ ] Backend and frontend image tags are immutable `sha-*` tags from that workflow run.
- [ ] No real/private logs, credentials, `.env` files, model secrets, or tokens are in Git/history.
- [ ] `docker compose ... config --quiet` passes using deployment-managed secrets.
- [ ] `JWT_SECRET`, `SENSOR_INGEST_TOKEN`, database password, issuer, audience, and HTTPS origin
      are set to non-example values.
- [ ] PostgreSQL custom-format backup completed, is stored off-host, and `pg_restore --list` passes.
- [ ] Migration revision and downgrade/restore impact were reviewed.
- [ ] Previous image tags and database restoration instructions are recorded.

## Deploy and verify

- [ ] Pull the exact SHA-tagged image pair and start the stack.
- [ ] PostgreSQL, backend, and frontend report healthy with no restart loop.
- [ ] `alembic current` equals the expected reviewed head.
- [ ] Public HTTPS is valid; HTTP redirects to HTTPS; only the frontend is externally reachable.
- [ ] Security headers and restrictive CORS origin are present.
- [ ] First-owner setup is available only on an empty database, then returns `409`.
- [ ] Login, sensor heartbeat/device state, alerts, incident timeline, explanation, and graph work.
- [ ] Administrator audit view is role-restricted and records sensitive actions.
- [ ] A synthetic analysis creates an explainable alert and graph while every recommendation remains
      pending, human-approved, and non-executing.
- [ ] Logs contain no password, JWT, database URL, authorization header, or private event payload.
- [ ] Sensor command lines are hashed, ingestion deduplicates retries, and no remediation executes.

## After deployment

- [ ] Monitor health, error rates, authentication failures, rate limits, restarts, disk, and database
      capacity during the observation window.
- [ ] Record image digests, migration revision, validation evidence, and any known limitations.
- [ ] Keep the pre-release backup and previous images through the retention window.
- [ ] If any acceptance item fails, stop traffic and execute the documented rollback.
