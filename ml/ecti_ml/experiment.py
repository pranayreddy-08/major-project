import argparse
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import shap
import sklearn
import torch

from ecti_ml.baseline import train_logistic_baseline
from ecti_ml.config import PreprocessingConfig
from ecti_ml.explainability import explain_logistic_prediction
from ecti_ml.gnn import train_graphsage
from ecti_ml.preprocessing import prepare_frame


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_experiment(
    dataset_path: Path,
    preprocessing_path: Path,
    experiment_path: Path,
) -> dict[str, object]:
    preprocessing_config = PreprocessingConfig.from_json(preprocessing_path)
    experiment_config = _load_json(experiment_path)
    frame = pd.read_csv(dataset_path).drop_duplicates()
    frame[preprocessing_config.timestamp_column] = pd.to_datetime(
        frame[preprocessing_config.timestamp_column], utc=True, errors="raise"
    )
    frame = frame.sort_values(preprocessing_config.timestamp_column, kind="stable").reset_index(
        drop=True
    )
    prepared = prepare_frame(frame, preprocessing_config)
    positive_label = str(experiment_config["positive_label"])
    random_state = int(experiment_config["random_state"])
    baseline = train_logistic_baseline(
        prepared,
        positive_label=positive_label,
        random_state=random_state,
    )
    gnn_config = experiment_config["graphsage"]
    if not isinstance(gnn_config, dict):
        raise ValueError("graphsage experiment configuration must be an object")
    graphsage = train_graphsage(
        prepared,
        frame,
        positive_label=positive_label,
        window_minutes=int(experiment_config["correlation_window_minutes"]),
        hidden_size=int(gnn_config["hidden_size"]),
        learning_rate=float(gnn_config["learning_rate"]),
        weight_decay=float(gnn_config["weight_decay"]),
        max_epochs=int(gnn_config["max_epochs"]),
        patience=int(gnn_config["patience"]),
        random_state=random_state,
    )
    explanation = explain_logistic_prediction(
        baseline.model,
        prepared.train.features,
        prepared.test.features[0],
        prepared.feature_names,
    )

    return {
        "experiment_version": experiment_config["experiment_version"],
        "dataset": {
            "version": preprocessing_config.dataset_version,
            "sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
            "rows": len(frame),
        },
        "preprocessing_version": preprocessing_config.config_version,
        "split_rows": {
            "train": len(prepared.train.labels),
            "validation": len(prepared.validation.labels),
            "test": len(prepared.test.labels),
        },
        "models": {
            "logistic_regression": {
                "validation": baseline.validation.as_dict(),
                "test": baseline.test.as_dict(),
            },
            "graphsage": {
                "validation": graphsage.validation.as_dict(),
                "test": graphsage.test.as_dict(),
                "epochs_trained": graphsage.epochs_trained,
            },
        },
        "test_comparison": {
            "graphsage_minus_logistic_f1": graphsage.test.f1 - baseline.test.f1,
            "graphsage_minus_logistic_roc_auc": (
                graphsage.test.roc_auc - baseline.test.roc_auc
            ),
        },
        "example_shap_explanation": explanation.as_dict(),
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "shap": shap.__version__,
            "torch": torch.__version__,
            "device": "cpu",
        },
        "limitations": [
            "The synthetic dataset is small and label patterns are intentionally simple.",
            "These metrics validate the pipeline and must not be presented as real-world efficacy.",
            "Graph evidence is correlational and does not establish causality.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the reproducible Phase 4 model comparison")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--preprocessing-config", type=Path, required=True)
    parser.add_argument("--experiment-config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = run_experiment(
        args.dataset,
        args.preprocessing_config,
        args.experiment_config,
    )
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")


if __name__ == "__main__":
    main()
