# Phase 7 demonstration script

## Before the presentation

1. Run `docker compose up --build -d` and wait for all three services to become healthy/running.
2. Confirm <http://localhost:8000/health>, <http://localhost:8000/docs>, and
   <http://localhost:5173>.
3. On a fresh database, create your own owner account in the one-time setup screen.
4. Confirm **This device** shows an online Windows sensor.
5. Run the commands in `docs/testing.md` and retain the acceptance and experiment JSON records.

## Five-minute walkthrough

1. **Problem and safety (30 seconds):** explain that ECTI is decision support. Point out that it
   recommends actions but has no execution endpoint and always requires human approval.
2. **Installed collection and access (45 seconds):** show the online endpoint sensor, then sign in
   with the owner account you created. Mention Argon2id, expiring JWTs, bounded input, deduplication,
   audit logging, and that no preset credentials exist.
3. **Threat scenario (60 seconds):** open **Intelligence > Threat scenarios**, run Credential attack,
   and compare its expected and actual Attack labels. Point out confidence, risk, graph nodes, and
   the zero stored events/alerts proof.
4. **Agent handoffs (45 seconds):** use the same result to walk through Detection, Correlation, Risk,
   Explainability, and Response. Show the human gate and that automatic execution is disabled.
5. **Classification range (30 seconds):** run Suspicious tool activity and Normal activity. Explain
   why dual-use tooling is Suspicious while routine behavior remains Benign with no incident.
6. **Explainability and graph (45 seconds):** show evidence and readable reasoning, then use an
   attack scenario's graph output. State that correlation/model evidence does not prove causality.
7. **Models and GNN (45 seconds):** show that the live scenario uses the deterministic baseline.
   Then open **Models & GNN** for the offline Logistic Regression and GraphSAGE comparison; do not
   claim GraphSAGE is the live endpoint detector.
8. **Evaluation and acceptance (30 seconds):** open the retained experiment and acceptance JSON
   records. Show the confusion counts, known false negative, and passed raw-log-to-graph criteria.

## Questions to anticipate

- **Is it production ready?** No. It is an installed explainable prototype with real bounded host
  telemetry; it still lacks full EDR coverage, tamper protection, operational load evidence, and
  managed monitoring/backups.
- **Why Logistic Regression and GraphSAGE?** The former provides a transparent baseline; the latter
  tests causal prior-neighbor aggregation on the identical chronological split.
- **Can it block an IP?** No. `block_ip` is advisory data only and must be approved outside ECTI.
- **What failed?** Both models missed one synthetic port scan in the 18-row test partition; the exact
  failure is recorded for future improvement.
