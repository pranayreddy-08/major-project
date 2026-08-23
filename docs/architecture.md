# Foundation architecture

The Phase 2 development environment has three services managed by Docker Compose.

```mermaid
flowchart LR
    Browser[Analyst browser] -->|HTTP :5173| Frontend[React + TypeScript + Cytoscape]
    Frontend -->|JWT API :8000| Backend[FastAPI]
    Backend -->|SQL :5432| Database[(PostgreSQL)]
```

The backend owns validation and persistence. The frontend never connects directly to the database.
Browser requests from configured `CORS_ORIGINS` are accepted by the backend; the default permits the
local Vite development server at `http://localhost:5173`.
Offline ML training and evaluation live under `ml/`. The backend's bounded Phase 5 agents integrate
the intelligence components through strict service contracts and a failure-aware coordinator.

## Intelligence workflow

```mermaid
flowchart LR
    Coordinator --> Detection
    Detection --> Correlation
    Correlation --> Risk
    Detection --> Risk
    Correlation --> Explainability
    Risk --> Explainability
    Risk --> Response
    Response --> Approval[Human approval gate]
```

Every arrow is a validated `phase5-v1` Pydantic handoff. The coordinator returns ordered audit
digests and keeps the approval gate pending; no response component has an execution capability.

## Authentication and analyst surface

```mermaid
flowchart LR
    Login[OAuth2 password form] --> Auth[Argon2 verification]
    Auth --> Token[Signed expiring JWT]
    Token --> RBAC{Database role}
    RBAC -->|Analyst| Dashboard[Dashboard and analysis APIs]
    RBAC -->|Administrator| Audit[Audit-log API]
    Dashboard --> Store[(PostgreSQL records)]
    Audit --> Store
```

The browser keeps the bearer token in memory, calls only versioned backend endpoints, and never
connects to PostgreSQL. The server reloads account state for each token-authenticated request.

## Phase 7 acceptance path

```mermaid
flowchart LR
    Raw[Versioned raw sample logs] --> Normalize[Validate + normalize + deduplicate]
    Normalize --> Detect[Detection findings]
    Detect --> Correlate[Incident correlation]
    Correlate --> Graph[Visual attack graph]
    Detect --> Risk[Transparent risk score]
    Correlate --> Risk
    Risk --> Explain[Evidence + limitations]
    Risk --> Recommend[Advisory recommendations]
    Graph --> API[Dashboard API contract]
    Explain --> API
    Recommend --> Approval[Human approval pending]
```

`backend/app/acceptance.py` executes this bounded path with the versioned synthetic sample and
records counts, response time, input hash, safety state, and pass/fail criteria. API contract tests
exercise authenticated workflow responses; the Docker validation additionally checks the
PostgreSQL-backed analyst endpoints used by the React dashboard.

## Service boundaries

| Component | Current responsibility | Later responsibility |
| --- | --- | --- |
| Frontend | Authenticated analyst dashboard and interactive attack graph | Additional accessibility and operational views |
| Backend | Auth, RBAC, rate limiting, platform APIs, agents, audit logging | External identity and deployment integrations |
| PostgreSQL | Users, events, alerts, incidents, graphs, explanations, feedback, audits | Migration-managed production persistence |
| ML | Preprocessing, Logistic Regression, SHAP, causal GraphSAGE | Versioned model artifacts and additional training |
