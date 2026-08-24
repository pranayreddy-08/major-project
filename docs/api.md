# Versioned API

FastAPI exposes `/api/v1`; interactive OpenAPI is at `/docs`. A fresh database has no preset
credentials.

## Authentication and first run

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/auth/setup-status` | Public, rate limited | Report whether the first owner must be created |
| POST | `/api/v1/auth/setup` | Public only before initialization | Atomically create the initial administrator |
| POST | `/api/v1/auth/token` | Public, rate limited | Exchange form credentials for a bearer token |
| GET | `/api/v1/auth/me` | Authenticated | Read the current account |

`/auth/setup` accepts `username`, `full_name`, and a 12–128 character `password`. It succeeds
only while the account table is empty and then returns the same token contract as login.

After creating your owner in the browser, an API login looks like:

```powershell
$token = Invoke-RestMethod -Uri http://localhost:8000/api/v1/auth/token -Method Post `
  -ContentType application/x-www-form-urlencoded `
  -Body @{username='your-owner'; password='your-private-password'}
$headers = @{Authorization="Bearer $($token.access_token)"}
```

## Endpoint sensors

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/sensors/ingest` | `X-Sensor-Token` | Heartbeat and bounded event batch, maximum 500 |
| GET | `/api/v1/sensors` | Analyst/admin | List device identity, capabilities, heartbeat, and state |
| GET | `/api/v1/sensors/status` | Analyst/admin | Sensor totals and configured/online state |

The sensor token is separate from user JWTs. Event keys are restricted, deduplicated per sensor, and
link each accepted source signal to its normalized event.

## Investigation platform

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| GET/POST | `/api/v1/platform/events` | Analyst/admin | List or persist normalized events |
| GET | `/api/v1/platform/overview` | Analyst/admin | Counts, severities, recent activity, and model state |
| GET | `/api/v1/platform/alerts` | Analyst/admin | Filtered alert queue |
| GET | `/api/v1/platform/alerts/{id}` | Analyst/admin | Alert detail |
| GET | `/api/v1/platform/alerts/{id}/explanations` | Analyst/admin | Evidence and limitations |
| GET | `/api/v1/platform/alerts/{id}/recommendations` | Analyst/admin | Human-approved recommendations |
| GET | `/api/v1/platform/incidents` | Analyst/admin | Risk-ordered incidents |
| GET | `/api/v1/platform/incidents/{id}` | Analyst/admin | Correlated incident |
| GET | `/api/v1/platform/incidents/{id}/graph` | Analyst/admin | Cytoscape nodes and edges |
| POST | `/api/v1/platform/analysis/run` | Analyst/admin | Run and optionally persist the workflow |
| GET | `/api/v1/platform/workflows/recent` | Analyst/admin | Recent audited agent steps, timing, model, and safety gate |
| GET | `/api/v1/platform/models` | Analyst/admin | Runtime and offline-evaluated model catalog with bounded metrics |
| GET/POST | `/api/v1/platform/feedback` | Analyst/admin | Read or record analyst verdicts |
| GET | `/api/v1/platform/audit-logs` | Administrator | Recent audit records |

Recommendations always have human approval required and automatic execution disabled. Normal API
errors use `401` for invalid identity, `403` for insufficient role, `404` for missing resources,
`409` for completed first-run setup, `422` for invalid input, and `429` for rate limits.
