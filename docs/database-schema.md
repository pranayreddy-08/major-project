# Initial database schema

The SQLAlchemy metadata in `backend/app/models/entities.py` is the source of truth for the Phase 2
schema. During local development, the backend container creates missing tables before starting the
API. Formal versioned migrations will replace `create_all` before deployment.

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

UUIDs are used for primary keys. Event time and ingestion time are stored separately, and all
application timestamps must include a timezone. Flexible source-specific details are stored in JSON
`attributes` fields; frequently queried common fields remain typed columns and are indexed.
