# Phase 6 API

The FastAPI service exposes versioned endpoints under `/api/v1`. Interactive OpenAPI documentation
is available at `/docs`, and the machine-readable contract is available at `/openapi.json`.

Except for the token endpoint and `/health`, every endpoint requires an
`Authorization: Bearer <token>` header. Component intelligence/workflow endpoints from Phases 4 and
5 are protected as well.

## Authentication

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/auth/token` | Public, rate limited | Exchange OAuth2 form credentials for a 30-minute bearer token |
| GET | `/api/v1/auth/me` | Analyst or administrator | Read the authenticated account |

Local synthetic-demo accounts are created only outside production:

| Username | Default local password | Role |
| --- | --- | --- |
| `analyst` | `analyst-demo-only` | Analyst |
| `admin` | `admin-demo-only` | Administrator |

Override both passwords and `JWT_SECRET` through environment variables. Production configuration
rejects the documented local defaults.

```powershell
$token = Invoke-RestMethod `
  -Uri http://localhost:8000/api/v1/auth/token `
  -Method Post `
  -ContentType application/x-www-form-urlencoded `
  -Body @{username='analyst'; password='analyst-demo-only'}
$headers = @{Authorization="Bearer $($token.access_token)"}
```

## Analyst platform

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/platform/overview` | Analyst/admin | Alert/incident/event counts, severity distribution, model health |
| GET | `/api/v1/platform/events` | Analyst/admin | List normalized events with a bounded `limit` query |
| POST | `/api/v1/platform/events` | Analyst/admin | Validate and persist one normalized event |
| GET | `/api/v1/platform/alerts` | Analyst/admin | Search/filter the priority queue |
| GET | `/api/v1/platform/alerts/{id}` | Analyst/admin | Read one alert |
| GET | `/api/v1/platform/alerts/{id}/explanations` | Analyst/admin | Read stored explanations and evidence |
| GET | `/api/v1/platform/alerts/{id}/recommendations` | Analyst/admin | Generate safe response recommendations |
| GET | `/api/v1/platform/incidents` | Analyst/admin | List incidents ordered by risk |
| GET | `/api/v1/platform/incidents/{id}` | Analyst/admin | Read incident, correlated alerts, and graph |
| GET | `/api/v1/platform/incidents/{id}/graph` | Analyst/admin | Read Cytoscape-compatible nodes/edges |
| POST | `/api/v1/platform/analysis/run` | Analyst/admin | Run the Phase 5 coordinator and optionally persist output |
| GET | `/api/v1/platform/feedback` | Analyst/admin | List analyst feedback |
| POST | `/api/v1/platform/feedback` | Analyst/admin | Record a verdict/comment for an alert or incident |
| GET | `/api/v1/platform/audit-logs` | Administrator | Read the most recent security audit entries |

Run and persist a workflow using the shared fixture:

```powershell
$payload = Get-Content backend\tests\fixtures\phase5-workflow-v1.json -Raw |
  ConvertFrom-Json
$payload | Add-Member -NotePropertyName persist -NotePropertyValue $true
$result = Invoke-RestMethod `
  -Uri http://localhost:8000/api/v1/platform/analysis/run `
  -Method Post `
  -ContentType application/json `
  -Headers $headers `
  -Body ($payload | ConvertTo-Json -Depth 10)
```

The result contains the complete coordinator envelope plus stored event/alert UUIDs. Response
recommendations always include `requires_human_approval=true` and `automatic_execution=false`.

## Validation and errors

- `401`: missing, invalid, expired, or account-mismatched token.
- `403`: valid identity without the required role.
- `404`: requested alert, incident, or referenced feedback target does not exist.
- `422`: Pydantic input validation failure.
- `429`: rate limit exceeded; retry timing is returned through `Retry-After`.

Unexpected request fields are rejected by the normalized event, intelligence, and workflow
contracts. Intelligence/workflow requests accept at most 1,000 events, feedback comments accept at
most 2,000 characters, and list endpoints enforce hard maximum limits to prevent unbounded work or
responses. Individual malformed records are isolated by file ingestion adapters before API use;
malformed JSON documents fail before partial processing.
