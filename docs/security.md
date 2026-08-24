# Security design

## Identity and access

- A fresh installation contains no users. `POST /api/v1/auth/setup` can create exactly one initial
  administrator and returns `409` after setup. PostgreSQL locks the account table during creation
  to prevent concurrent first-owner races.
- Passwords are salted Argon2id hashes. Tokens are signed, expire after 30 minutes by default, pin
  the permitted algorithm, and validate subject, role, issuer, audience, issue time, expiry, and ID.
- Each authenticated request reloads the active account and role from PostgreSQL.
- Browser tokens stay in React memory. They are not stored in local storage or cookies.
- Analysts can use investigation APIs; administrators can additionally read audit logs.
- Login, setup, ingestion, analysis, and feedback actions create durable audit records.
- Public and authenticated endpoints use bounded inputs and sliding-window rate limits.

## Endpoint sensor boundary

The browser cannot inspect the operating system. The Windows sensor is a separate local process that
collects a narrow set of defensive signals and sends bounded batches to the loopback API using
`X-Sensor-Token`. Token comparison is constant-time, ingestion fails closed when the token is not
configured, event keys are deduplicated, and online status uses server receipt time.

The desktop installer generates independent random PostgreSQL, JWT, and sensor secrets. Its Docker
ports bind only to `127.0.0.1`. Non-loopback sensor API URLs must use HTTPS. The sensor hashes
suspicious process command lines before upload and does not collect file contents, browser history,
documents, keystrokes, or credentials.

The installer is per-user and does not create an elevated service or persistence task. This avoids
silently granting SYSTEM privileges. Some protected Windows Security log channels may therefore be
unavailable; enabling broader elevated collection must be a separate explicit administrator choice.

## Environment requirements

`JWT_SECRET`, `SENSOR_INGEST_TOKEN`, and the database password must be unique secrets of at least
32 characters in production. Configure `JWT_ISSUER`, `JWT_AUDIENCE`, CORS origins, and token
expiry consistently. Never commit the generated desktop `.env` or sensor configuration.

## Current limitations

- The platform detects and explains supported signals; it is not a replacement for Microsoft
  Defender or a professionally managed EDR.
- Response actions remain recommendations. There is no automatic remediation endpoint.
- Process-pattern and port rules are intentionally narrow and can produce false positives.
- The in-process rate limiter is not suitable for a multi-replica public service without a shared
  limiter and trusted-proxy policy.
- HS256 is suitable for this single-service local layout; distributed services should assess
  asymmetric signing and formal rotation.
- Audit rows are durable but do not yet have external tamper-evident archival.
- Operators must back up PostgreSQL before migrations; a mechanical downgrade is not proof of
  data-preserving rollback.
