from pathlib import Path

import numpy as np
import pandas as pd
import torch

from ecti_ml.baseline import train_logistic_baseline
from ecti_ml.config import PreprocessingConfig
from ecti_ml.explainability import explain_logistic_prediction
from ecti_ml.gnn import build_causal_adjacency, train_graphsage
from ecti_ml.preprocessing import prepare_frame

PROJECT_ROOT = Path(__file__).parents[2]


def prepared_sample() -> tuple[pd.DataFrame, object]:
    frame = pd.read_csv(PROJECT_ROOT / "data/samples/synthetic-events-v1.csv")
    config = PreprocessingConfig.from_json(PROJECT_ROOT / "ml/configs/preprocessing-v1.json")
    return frame, prepare_frame(frame, config)


def test_logistic_baseline_reports_required_metrics_and_shap_evidence() -> None:
    _, prepared = prepared_sample()

    result = train_logistic_baseline(prepared)
    explanation = explain_logistic_prediction(
        result.model,
        prepared.train.features,
        prepared.test.features[0],
        prepared.feature_names,
        top_k=5,
    )

    assert result.test.samples == 18
    assert (
        result.test.true_negative
        + result.test.false_positive
        + result.test.false_negative
        + result.test.true_positive
        == result.test.samples
    )
    assert 0 <= result.test.false_positive_rate <= 1
    assert 0 <= result.test.roc_auc <= 1
    assert result.test.inference_time_ms >= 0
    assert explanation.method == "shap-linear"
    assert len(explanation.contributions) == 5
    assert 0 <= explanation.predicted_probability <= 1
    assert "does not establish causality" in explanation.limitations


def test_causal_adjacency_never_uses_future_neighbors() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": [
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:01:00Z",
                "2026-01-01T00:02:00Z",
            ],
            "source_ip": ["192.0.2.1"] * 3,
        }
    )

    adjacency = build_causal_adjacency(
        frame,
        timestamp_column="timestamp",
        entity_columns=("source_ip",),
        window_minutes=5,
    )

    assert adjacency[0].sum() == 0
    assert adjacency[1, 0] == 1
    assert adjacency[2, 0] == adjacency[2, 1] == 0.5
    assert torch.triu(adjacency).sum() == 0

    cross_role = frame.copy()
    cross_role["source_ip"] = ["192.0.2.1", "192.0.2.2", "192.0.2.3"]
    cross_role["destination_ip"] = ["198.51.100.1", "192.0.2.1", "198.51.100.3"]
    cross_role_adjacency = build_causal_adjacency(
        cross_role,
        timestamp_column="timestamp",
        entity_columns=("source_ip", "destination_ip"),
        window_minutes=5,
    )
    assert cross_role_adjacency[1, 0] == 1


def test_graphsage_uses_same_temporal_partitions_as_baseline() -> None:
    frame, prepared = prepared_sample()

    result = train_graphsage(
        prepared,
        frame,
        max_epochs=40,
        patience=8,
        hidden_size=16,
    )

    assert result.validation.samples == len(prepared.validation.labels)
    assert result.test.samples == len(prepared.test.labels)
    assert len(result.test_probabilities) == len(prepared.test.labels)
    assert np.isfinite(result.test_probabilities).all()
    assert 1 <= result.epochs_trained <= 40
