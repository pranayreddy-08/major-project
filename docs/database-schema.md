# Initial database schema

The SQLAlchemy metadata in `backend/app/models/entities.py` describes the application model, while
reviewed Alembic revisions in `backend/migrations/versions/` are the deployment source of truth.
Development, staging, and production Compose startup run `alembic upgrade head` before serving the
API. The initial revision is `bbfa5454db7e`.

| Table | Purpose |
| --- | --- |
| `asset_hosts` | Hosts/assets and their business criticality |
| `raw_events` | Immutable source records before normalization |
| `normalized_events` | Common event representation used by downstream modules |
| `alerts` | Detection results requiring analyst attention |
| `incidents` | Correlated groups of alerts and their risk state |
| `indicators_of_compromise` | IPs, domains, hashes, and other threat indicators |
| `attack_graph_nodes` | Entities represented in an attack graph |
| `attack_graph_edges` | Time-stamped relationships and evidence between graph nodes |
| `model_runs` | Model version, parameters, dataset version, metrics, and run status |
| `explanations` | Analyst-readable evidence associated with alerts |
| `analyst_feedback` | Analyst verdicts and comments for alerts/incidents |
| `user_accounts` | Argon2-hashed local accounts, active state, and analyst/administrator role |
| `audit_logs` | Durable security-sensitive action history and request-origin metadata |

UUIDs are used for primary keys. Event time and ingestion time are stored separately, and all
application timestamps must include a timezone. Flexible source-specific details are stored in JSON
`attributes` fields; frequently queried common fields remain typed columns and are indexed.

CI applies every revision to an empty PostgreSQL 17 database, runs `alembic check` for model/schema
drift, downgrades to `base`, and upgrades again. A release still requires a verified backup before
migration. Destructive or lossy changes must use an expand/migrate/contract sequence rather than a
single irreversible revision.

`app.db.migrate` supports the one-time Phase 6-to-Phase 8 transition for development/staging
volumes: it stamps the initial head only when all expected application tables are present and no
Alembic version table exists. Partial schemas fail, and production legacy schemas require explicit
operator review rather than automatic stamping.
