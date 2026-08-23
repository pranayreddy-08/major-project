# Phase 7 testing and acceptance

## Automated test matrix

| Layer | Coverage | Command |
| --- | --- | --- |
| Backend unit/API | parsing, normalization, duplicates, schemas, scoring, graphs, response safety, auth/RBAC, audit, coordinator failure isolation | `python -m pytest backend\tests` |
| Backend adversarial | missing/malformed fields, malformed JSON, invalid IP/severity, duplicate records, epoch/naive timestamps, extra fields, oversized batches/comments | `python -m pytest backend\tests\test_adversarial.py` |
| Full synthetic path | raw JSON aliases -> normalized events -> findings -> incident -> risk -> explanation -> graph -> advisory response | `python -m pytest backend\tests\test_acceptance.py` |
| ML | leakage-safe preprocessing, Logistic Regression, SHAP, causal adjacency, GraphSAGE, metrics, experiment evidence | `python -m pytest ml\tests` |
| Frontend | secure login defaults, rejected credentials, bearer-authenticated dashboard loading | `npm test` from `frontend` |
| Static/build | Python Ruff, TypeScript checks, Vite production bundle, Compose rendering | `python -m ruff check backend ml`; `npm run build`; `docker compose config --quiet` |

At Phase 7 completion, the repository contains 43 backend tests, 8 ML tests, and 3 frontend tests.
Every check above is intended to run without private data.

## Prototype acceptance criteria

The versioned input is `data/samples/phase7-acceptance-events-v1.json`; the recorded result is
`docs/acceptance/phase7-synthetic-v1.json`. Acceptance requires all of the following:

1. all three raw records normalize without errors;
2. at least one attack finding and one correlated incident are created;
3. risk and analyst-readable explanation records are present;
4. the attack graph has both nodes and edges and is suitable for the dashboard graph contract;
5. at least one recommendation is returned, every recommendation requires human approval, and none
   can execute automatically;
6. the local in-process path completes within 2,000 ms.

The recorded run passed all criteria in 3.13 ms, creating 3 findings, 1 incident, 2 explanations,
5 recommendations, 4 nodes, and 6 edges. The generous threshold prevents ordinary workstation
variation from making the test flaky. It measures the small in-process synthetic path, not network,
database, browser-rendering, concurrent-load, or production latency.

## Model evaluation evidence

`docs/experiments/phase7-synthetic-v1.json` records the dataset version and SHA-256 digest, expanded
feature names, chronological split sizes, full parameter configuration, environment versions,
precision, recall, F1, ROC-AUC, false-positive rate, inference time, TN/FP/FN/TP counts, SHAP evidence,
and observed failures. Both test confusion matrices contain 15 TN, 0 FP, 1 FN, and 2 TP. The single
false negative is retained with its row, timestamp, event type, source IP, and predicted probability.

## Known evaluation limits

- The 120-row dataset is intentionally synthetic and cannot establish real-world efficacy.
- The frontend tests mock API responses; the Docker smoke run verifies live service connectivity.
- The acceptance runner validates one representative attack chain, not throughput or concurrency.
- Graph links and SHAP contributions explain system behavior but do not establish causality.
- Authorization tests use controlled test identities; external identity providers are outside scope.
