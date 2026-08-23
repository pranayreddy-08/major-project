# Explainable Cyber Threat Intelligence Platform

## Project goal

Build a cybersecurity decision-support platform that collects security events, detects suspicious activity, connects related events into attack paths, estimates risk, explains each prediction, and recommends mitigation actions. The final system will use Graph Neural Networks (GNNs), conventional machine-learning models, explainable AI (XAI), and a multi-agent workflow behind a real-time dashboard.

## Proposed technology stack

- Frontend: React.js, TypeScript, Cytoscape.js for attack-graph visualisation
- Backend: Python 3.10+, FastAPI, Pydantic, SQLAlchemy
- Database: PostgreSQL
- Data processing and ML: Pandas, scikit-learn, XGBoost, PyTorch, PyTorch Geometric
- Explainability: SHAP; use LIME only where it adds value
- Development and delivery: GitHub, Git, Docker Compose, GitHub Actions

## Development setup

### Run the complete stack with Docker

Docker Compose starts PostgreSQL, creates the initial database tables, and runs the backend and
frontend development servers.

```powershell
Copy-Item .env.example .env
docker compose up --build
```

The example environment file intentionally contains no values. Compose uses safe local defaults;
set values in `.env` when different local credentials or ports are needed.

After startup, open:

- Frontend: <http://localhost:5173>
- Backend health check: <http://localhost:8000/health>
- Interactive API documentation: <http://localhost:8000/docs>

Stop the services with `docker compose down`. The PostgreSQL data remains in a named Docker volume.
Use `docker compose down --volumes` only when intentionally resetting all local database data.

### Run services directly

Install Python 3.10 or newer and Node.js 22 or newer. From the project root on Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".\backend[dev]"
python -m pip install -e ".\ml[dev]"
pytest backend\tests
pytest ml\tests

Set-Location frontend
npm ci
npm run build
Set-Location ..
```

Start PostgreSQL separately and configure `DATABASE_URL` in `.env`, then run:

```powershell
python -m app.db.init_db
uvicorn app.main:app --app-dir backend --reload
Set-Location frontend
npm run dev
```

The initial architecture is documented in `docs/architecture.md`, the database entities in
`docs/database-schema.md`, and the common event contract in `docs/event-schema.md`.

### Foundation status

Phase 2 is complete. The repository now includes the six planned module directories, reproducible
and pinned backend/frontend dependencies, secret-safe environment configuration, a three-service
Docker Compose development stack, the initial SQLAlchemy database schema, and a validated common
event contract. Backend tests, frontend compilation, and `docker compose config --quiet` are the
foundation acceptance checks.

### Data-pipeline status

Phase 3 is complete. CSV, JSON/NDJSON, and syslog adapters preserve raw records while producing the
common event schema; invalid records are isolated and SHA-256 checksums remove duplicates. The ML
package performs missing-value handling, categorical encoding, numeric scaling, and chronological
train/validation/test splitting without fitting on future data. A deterministic synthetic dataset,
dataset registry, versioned preprocessing configuration, and provenance/licensing catalogue make the
pipeline reproducible without private logs.

Recreate the synthetic sample:

```powershell
python -m app.ingestion.synthetic `
  --output data\samples\synthetic-events-v1.csv `
  --manifest data\samples\synthetic-events-v1.manifest.json `
  --count 120 `
  --seed 42
```

Normalize it into separate, ignored raw and normalized outputs:

```powershell
python -m app.ingestion.cli data\samples\synthetic-events-v1.csv `
  --format csv `
  --log-source synthetic `
  --raw-output data\processed\synthetic-v1.raw.jsonl `
  --normalized-output data\processed\synthetic-v1.normalized.jsonl
```

Verify the chronological feature-preparation split:

```powershell
python -m ecti_ml.cli data\samples\synthetic-events-v1.csv `
  --config ml\configs\preprocessing-v1.json
```

The complete workflow and governance rules are documented in `docs/data-pipeline.md` and
`docs/datasets.md`.

### Intelligence status

Phase 4 is complete. The platform now includes an explainable Logistic Regression baseline,
rule-based event correlation, deterministic attack-graph construction, causal GraphSAGE event
classification, transparent risk scoring, SHAP and graph-evidence explanations, and a safe response
catalogue. Every response remains a recommendation with mandatory human approval and no automatic
execution path.

The versioned synthetic comparison produced the following test metrics:

| Model | Precision | Recall | F1 | ROC-AUC | False-positive rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Logistic Regression | 1.000 | 0.667 | 0.800 | 0.800 | 0.000 |
| Causal GraphSAGE | 1.000 | 0.667 | 0.800 | 0.778 | 0.000 |

These values validate the pipeline on 18 intentionally simple synthetic test rows; they are not a
claim of real-world effectiveness. Reproduce the comparison with:

```powershell
python -m ecti_ml.experiment `
  --dataset data\samples\synthetic-events-v1.csv `
  --preprocessing-config ml\configs\preprocessing-v1.json `
  --experiment-config ml\configs\phase4-experiment-v1.json `
  --output docs\experiments\phase4-synthetic-v1.json
```

Module design, the risk formula, API paths, response-safety guarantees, and experiment limitations
are documented in `docs/intelligence.md`.

## Development plan

### Phase 1 - Create and connect the GitHub repository

1. Create a private GitHub repository named `explainable-cyber-threat-intelligence-platform` under your GitHub account. Add the faculty guide only if project access or review is required.
2. Create a clear repository description, add this README, choose a Python `.gitignore`, and select an open-source licence only if the project is intended to be public.
3. Keep `main` as the stable branch. Use feature branches for meaningful changes, then merge them only after you have tested and reviewed the changes yourself.
4. Configure your Git identity once:

   ```bash
   git config --global user.name "Your Name"
   git config --global user.email "your-email@example.com"
   ```

5. To link the existing local project folder to the new remote repository, run these commands from the project folder:

   ```bash
   git init
   git add .
   git commit -m "Initial project setup"
   git branch -M main
   git remote add origin https://github.com/ORG_OR_USERNAME/explainable-cyber-threat-intelligence-platform.git
   git push -u origin main
   ```

   Replace `ORG_OR_USERNAME` with the GitHub owner. Use the SSH remote URL instead if SSH keys have been configured.

6. To work from another computer or to get a clean local copy later, clone the repository:

   ```bash
   git clone https://github.com/ORG_OR_USERNAME/explainable-cyber-threat-intelligence-platform.git
   cd explainable-cyber-threat-intelligence-platform
   ```

7. For every new task, create a focused branch, make small commits, push it, and open a pull request:

   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/data-ingestion
   # make and test changes
   git add .
   git commit -m "Add log ingestion skeleton"
   git push -u origin feature/data-ingestion
   ```

   Suggested branch prefixes: `feature/`, `fix/`, `docs/`, `experiment/`, and `chore/`.

### Phase 2 - Establish the project foundation

1. Create the initial structure:

   ```text
   frontend/          React dashboard
   backend/           FastAPI service and API tests
   ml/                training, evaluation, and inference code
   data/              sample data only; never commit large/private raw datasets
   docs/              architecture, API, experiments, and meeting notes
   infra/             Docker, deployment, and CI configuration
   ```

2. Create a Python virtual environment, pin dependencies in `requirements.txt` or `pyproject.toml`, and document the exact setup commands.
3. Add `.env.example` containing variable names only. Keep secrets, API keys, database passwords, and real log files out of Git; use `.env` locally and deployment secrets in the hosting platform.
4. Add Docker Compose for local development: PostgreSQL, backend, and frontend should start together with one command.
5. Define the first database schema: assets/hosts, raw events, normalized events, alerts, incidents, indicators of compromise, attack graph nodes/edges, model runs, explanations, and analyst feedback.
6. Agree on an event schema based on fields such as timestamp, source IP, destination IP, user, host, protocol, action, severity, and log source. Normalize all inputs into this common format.

### Phase 3 - Data collection and preparation

1. Start with public, research-friendly data such as UNSW-NB15, CIC-IDS2017/CSE-CIC-IDS2018, and optionally MITRE ATT&CK technique mappings. Record dataset source, licence, version, features, and limitations in `docs/datasets.md`.
2. Build ingestion adapters for CSV first, then extend to JSON/syslog-style records. Store raw uploads separately from normalized records so the pipeline is reproducible.
3. Implement validation, timestamp parsing, duplicate removal, missing-value handling, categorical encoding, scaling, and train/validation/test splits that prevent time leakage.
4. Create an anonymised synthetic-log generator or a small sample dataset for demonstrations. The dashboard must work without real organisational logs.
5. Version datasets and experiment configurations. Never use a test set while tuning a model.

### Phase 4 - Build the intelligence and AI modules

Implement the system in small, independently testable increments.

1. **Baseline threat detection:** Train a simple, explainable baseline such as Logistic Regression, Random Forest, or XGBoost. Measure precision, recall, F1-score, ROC-AUC, false-positive rate, and inference time.
2. **Event correlation:** Link events through shared IP addresses, users, hosts, processes, time windows, and indicators. Build an initial rule-based correlation engine before adding GNNs.
3. **Attack graph construction:** Represent entities as nodes and relationships/events as time-stamped edges. Keep graph construction deterministic and expose the graph through the backend API.
4. **GNN model:** Train a GraphSAGE or GAT baseline for node/edge classification or risk scoring. Compare it against the non-graph baseline using the same evaluation split.
5. **Risk assessment:** Produce a transparent risk score from threat confidence, affected-asset criticality, attack stage, anomaly level, and event recency. Document the formula and the model inputs.
6. **Explainability:** Generate SHAP explanations for tabular-model predictions and graph-specific explanations or evidence paths for GNN results. Every alert should show why it was raised, the important features/evidence, confidence, and limitations.
7. **Response recommendation:** Begin with a safe, human-approved rule catalogue: block IP, isolate host, reset credentials, investigate endpoint, patch vulnerability, or monitor. The platform recommends actions; it must not automatically change security controls in the project prototype.

### Phase 5 - Create the multi-agent workflow

Use clearly separated services/components rather than uncontrolled autonomous agents.

1. **Detection agent:** runs anomaly and attack classification models.
2. **Correlation agent:** groups related events and maintains attack paths.
3. **Risk agent:** calculates severity and incident priority.
4. **Explainability agent:** prepares feature importance, supporting evidence, and analyst-readable explanations.
5. **Response agent:** maps confirmed risks to recommended mitigation steps.
6. **Coordinator:** passes structured JSON between agents, records every decision, handles failures, and ensures a human analyst remains the final approver.

Define an API contract and test data for each agent before integrating the full flow.

### Phase 6 - Build the dashboard and APIs

1. Implement FastAPI endpoints for event ingestion, alerts, incidents, attack graphs, model predictions, explanations, recommendations, feedback, and system health.
2. Add authentication and role-based access for analyst and administrator accounts. Hash passwords, validate all inputs, rate-limit public endpoints, and keep audit logs.
3. Build the React dashboard in this order:
   - Overview: alert counts, severity distribution, recent activity, and model health.
   - Alerts: searchable, filterable priority queue with alert details.
   - Incident view: correlated timeline, affected entities, and recommended actions.
   - Attack graph: interactive node-link visualisation with evidence on selection.
   - Explainability panel: prediction confidence, contributing signals, and clear reasons.
   - Feedback view: analyst confirmation/dismissal and comments for future improvement.
4. Keep APIs versioned (for example, `/api/v1/...`) and document every endpoint using FastAPI/OpenAPI plus examples in `docs/api.md`.

### Phase 7 - Testing, evaluation, and documentation

1. Write unit tests for parsing, normalization, scoring, graph construction, API validation, and response rules.
2. Add integration tests for the end-to-end path: sample logs -> normalized events -> alert -> correlation -> risk -> explanation -> dashboard API.
3. Test with adversarial and invalid input: missing fields, malformed logs, duplicate events, unusual timestamps, and unauthorised requests.
4. Track model experiments with dataset version, features, parameters, metrics, confusion matrix, and observed failure cases.
5. Define acceptance criteria for the prototype, for example: an uploaded sample log set creates an explainable alert and visual attack path within an agreed response time.
6. Maintain architecture diagrams, setup instructions, demo script, user guide, API documentation, and weekly progress notes in `docs/`.

### Phase 8 - Continuous integration and deployment

1. Add a GitHub Actions workflow that runs formatting, linting, backend tests, and frontend tests for every pull request. Do not allow failing checks to merge into `main`.
2. Build Docker images for the frontend and backend. Use environment variables for database URL, frontend API URL, CORS origins, JWT secret, and model/data paths.
3. First deploy a staging environment with synthetic data. A practical prototype layout is:

   ```text
   Browser -> React frontend -> FastAPI backend -> PostgreSQL
                                        -> ML/GNN inference service
   ```

4. Deploy the frontend to a static host and the backend/database to a suitable container or cloud platform. Configure HTTPS, restrictive CORS, secrets, database backups, health checks, and log monitoring.
5. Run database migrations as part of the release process. Never deploy schema changes manually without a backup and rollback plan.
6. Use a release checklist: tests pass, migration tested, environment variables set, synthetic demo works, endpoints are healthy, logs contain no secrets, and rollback version is known.
7. For the academic demonstration, deploy only anonymised/synthetic datasets and require human confirmation for every suggested response action.

## Suggested milestone sequence

1. Repository, documentation, local Docker setup, database skeleton.
2. CSV ingestion and normalized event storage.
3. Baseline threat detection and alert API.
4. Correlation engine and attack-graph API.
5. Risk scoring and explainability.
6. React dashboard and analyst feedback.
7. GNN integration and baseline comparison.
8. Multi-agent orchestration, testing, deployment, and final demo.

## Solo working agreement

- Use GitHub Issues to divide your work into small tasks with clear acceptance criteria.
- Link each pull request to its issue and include screenshots/API examples when relevant.
- Pull from `main` before starting work and resolve merge conflicts on the feature branch.
- Review your code for correctness, security, tests, and documentation - not only whether it runs locally.
- Record decisions, blockers, and model results in the repository so the final report and presentation remain easy to prepare.
