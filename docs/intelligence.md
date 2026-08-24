# Phase 4 intelligence modules

Phase 4 adds independently testable intelligence components. The platform remains decision support:
all response actions are recommendations and require a human analyst's approval.

## Baseline detection and comparison

The reproducible experiment uses `synthetic-events-v1`, the chronological 84/18/18 split from
`preprocessing-v1`, and a fixed random seed. Logistic Regression is the explainable tabular baseline.
A two-layer GraphSAGE implementation classifies the same event nodes with the same preprocessed
features and split boundaries.

The endpoint-serving workflow currently uses the deterministic
`severity-anomaly-baseline` version 1.0.0. Logistic Regression and GraphSAGE are implemented and
reproducibly evaluated offline, but are not loaded into the runtime FastAPI detector. The dashboard
labels this boundary explicitly; deploying GraphSAGE online requires a versioned model artifact,
runtime dependency/performance review, and live-data validation.

| Model | Test precision | Test recall | Test F1 | Test ROC-AUC | False-positive rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Logistic Regression | 1.000 | 0.667 | 0.800 | 0.800 | 0.000 |
| Causal GraphSAGE | 1.000 | 0.667 | 0.800 | 0.778 | 0.000 |

These numbers validate the implementation only. The synthetic labels deliberately follow simple
patterns, the test set contains only 18 rows, and the results must not be described as evidence of
real-world detection performance. Exact metrics, versions, inference timings, configuration, and an
example SHAP explanation are recorded in `docs/experiments/phase4-synthetic-v1.json`.

The Phase 7 evaluation record at `docs/experiments/phase7-synthetic-v1.json` additionally preserves
the complete expanded feature list, all experiment parameters, TN/FP/FN/TP confusion-matrix counts,
and each observed test failure. Both models missed the same synthetic port-scan row (row 107), which
is retained as an explicit limitation rather than hidden behind aggregate metrics.

Reproduce the experiment:

```powershell
python -m ecti_ml.experiment `
  --dataset data\samples\synthetic-events-v1.csv `
  --preprocessing-config ml\configs\preprocessing-v1.json `
  --experiment-config ml\configs\phase4-experiment-v1.json `
  --output docs\experiments\phase4-synthetic-v1.json
```

Use `ml/configs/phase7-evaluation-v1.json` and output
`docs/experiments/phase7-synthetic-v1.json` to reproduce the extended Phase 7 evidence.

## Correlation and graph construction

The rule engine links events inside a configurable time window when they share an IP address, user,
or host. Connected components become correlated incidents. IDs are hashes of canonical event/entity
data, so the same input produces the same incident, node, and edge identifiers regardless of input
order.

The attack graph represents IPs, users, and hosts as nodes. Time-stamped edges represent network
connections, user activity on hosts, and source observations. Graph evidence paths list the exact
edge and event IDs supporting a node while warning that correlation does not prove causality.

GraphSAGE uses event nodes and causal mean aggregation. A node can aggregate only earlier events in
the correlation window; it never reads a future neighbor. IP identity is shared across source and
destination roles.

## Risk formula

Risk formula `risk-v1` produces a score from 0 to 100:

```text
100 * (0.35 * threat confidence
     + 0.25 * asset criticality
     + 0.15 * attack stage
     + 0.15 * anomaly level
     + 0.10 * recency)
```

`recency = 0.5 ** (age_hours / 24)`, giving recency evidence a 24-hour half-life. Inputs are bounded
from 0 to 1, future timestamps cannot increase the value above fresh-event recency, and the API
returns each weighted component. Levels are low below 35, medium from 35, high from 65, and critical
from 85.

## Explainability

Logistic predictions use SHAP's linear explainer with the training partition as background. Each
explanation includes probability, base value, top signed feature contributions, and limitations.
Graph results use deterministic evidence paths through connected prior events. Neither explanation
method establishes causality or guarantees that a prediction is correct.

## Response catalogue

Rules can recommend `block_ip`, `isolate_host`, `reset_credentials`, `investigate_endpoint`,
`patch_vulnerability`, or `monitor`. Every returned item has:

```json
{
  "requires_human_approval": true,
  "automatic_execution": false
}
```

The prototype contains no connector or execution path that changes a firewall, identity system,
endpoint, or vulnerability-management platform.

## Versioned API

| Method and path | Purpose |
| --- | --- |
| `POST /api/v1/intelligence/correlations/build` | Correlate normalized events in a time window |
| `POST /api/v1/intelligence/attack-graphs/build` | Build a deterministic entity graph |
| `POST /api/v1/intelligence/risk/score` | Calculate transparent risk and components |
| `POST /api/v1/intelligence/recommendations` | Return human-approved response suggestions |

Request/response examples are available in FastAPI's generated documentation at `/docs` when the
backend is running.
