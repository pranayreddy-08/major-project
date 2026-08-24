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
3. **Overview and alert (45 seconds):** show counts and severity distribution. Open the priority
   queue, filter it, then select a suspicious alert.
4. **Explainability (45 seconds):** show confidence, important evidence, readable reasoning, and the
   limitation that correlation/model evidence does not prove causality.
5. **Incident and graph (60 seconds):** open the incident timeline and risk score, then the attack
   graph. Select entities and connect graph edges back to the correlated evidence.
6. **Human decision (45 seconds):** show advisory recommendations and submit analyst feedback.
   Reiterate that automatic execution remains false.
7. **Evaluation (45 seconds):** open `docs/experiments/phase7-synthetic-v1.json`. Show the confusion
   counts and retained false-negative row rather than quoting only aggregate scores.
8. **Acceptance (30 seconds):** open `docs/acceptance/phase7-synthetic-v1.json` and show that every
   raw-log-to-graph criterion passed within the local 2,000 ms limit.

## Questions to anticipate

- **Is it production ready?** No. It is an installed explainable prototype with real bounded host
  telemetry; it still lacks full EDR coverage, tamper protection, operational load evidence, and
  managed monitoring/backups.
- **Why Logistic Regression and GraphSAGE?** The former provides a transparent baseline; the latter
  tests causal prior-neighbor aggregation on the identical chronological split.
- **Can it block an IP?** No. `block_ip` is advisory data only and must be approved outside ECTI.
- **What failed?** Both models missed one synthetic port scan in the 18-row test partition; the exact
  failure is recorded for future improvement.
