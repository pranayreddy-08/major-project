# Phase 6 security design

Phase 6 adds prototype authentication and authorization without weakening the human-control
guarantees from earlier phases.

## Controls

- Passwords are stored as salted Argon2id hashes through `PasswordHash.recommended()` from
  `pwdlib`. Plaintext passwords are used only during the login request and are never stored.
- Access tokens are signed with HS256 and contain verified `sub`, `role`, `iss`, `aud`, `iat`,
  `exp`, and `jti` claims. The decoder pins the permitted algorithm instead of trusting the token
  header.
- The token subject uses a `username:` prefix to avoid identifier collisions.
- Every authenticated request reloads the account from PostgreSQL, verifies that it is active, and
  compares the current database role with the signed role.
- Analysts can use dashboard and analysis endpoints. Only administrators can read audit logs.
- Login attempts, event ingestion, workflow analysis, and feedback submissions write audit rows.
  Failed logins use a generic response and still perform a dummy Argon2 verification when the
  username is unknown.
- API calls use a sliding-window rate limiter. Login has a lower limit than authenticated API
  traffic and returns `429` plus `Retry-After` when full.
- Browser tokens remain in React memory. They are not written to local storage or cookies.
- CORS accepts only configured origins. The frontend never connects directly to PostgreSQL.

## Environment requirements

`JWT_SECRET`, `DEMO_ANALYST_PASSWORD`, and `DEMO_ADMIN_PASSWORD` must be replaced before using
`APP_ENVIRONMENT=production`; configuration validation rejects the local defaults. Use a randomly
generated secret of at least 32 characters and deployment-managed secrets rather than committing
values to Git.

Tokens expire after 30 minutes by default. Configure `JWT_ISSUER`, `JWT_AUDIENCE`, and
`ACCESS_TOKEN_EXPIRE_MINUTES` consistently across replicas.

## Prototype limitations

- The rate limiter is in-process and keyed by the directly connected client address. A multi-replica
  deployment needs a shared limiter (for example Redis) and an explicitly trusted proxy policy.
- HS256 is appropriate for the single-service prototype. A multi-service deployment should assess
  asymmetric signing and formal key rotation.
- `create_all` is still used for local development. Phase 8 must introduce reviewed migrations and
  rollback procedures.
- Development seed accounts/data are for synthetic local demonstrations only. They are not created
  when the app environment is production.
- Audit rows are durable in PostgreSQL but do not yet have external tamper-evident archival.
- The platform provides decision support, not autonomous response. There is no security-control
  execution endpoint.

The implementation follows FastAPI's documented OAuth2 bearer/JWT structure, uses pwdlib's
recommended Argon2 settings, and validates registered JWT expiration/issuer/audience claims.
