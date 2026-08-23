from pathlib import Path

import pandas as pd
import pytest

from ecti_ml.config import PreprocessingConfig
from ecti_ml.preprocessing import prepare_frame


def config() -> PreprocessingConfig:
    return PreprocessingConfig(
        config_version="test-v1",
        dataset_version="sample-v1",
        timestamp_column="timestamp",
        label_column="label",
        numeric_columns=("value",),
        categorical_columns=("category",),
        train_fraction=0.6,
        validation_fraction=0.2,
        test_fraction=0.2,
    )


def test_config_loads_versioned_split_policy() -> None:
    project_root = Path(__file__).parents[2]
    loaded = PreprocessingConfig.from_json(project_root / "ml/configs/preprocessing-v1.json")

    assert loaded.config_version == "preprocessing-v1"
    assert loaded.dataset_version == "synthetic-events-v1"
    assert loaded.train_fraction + loaded.validation_fraction + loaded.test_fraction == 1


def test_preprocessing_splits_before_fit_and_handles_unknown_categories() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": [f"2026-01-01T00:{minute:02d}:00Z" for minute in reversed(range(10))],
            "value": list(reversed(range(10))),
            "category": [
                "future",
                "future",
                "future",
                "future",
                "past",
                "past",
                "past",
                "past",
                "past",
                "past",
            ],
            "label": ["attack" if minute % 2 else "benign" for minute in reversed(range(10))],
        }
    )
    frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)

    prepared = prepare_frame(frame, config())

    assert len(prepared.train.labels) == 6
    assert len(prepared.validation.labels) == 2
    assert len(prepared.test.labels) == 2
    assert prepared.train.timestamps.max() <= prepared.validation.timestamps.min()
    assert prepared.validation.timestamps.max() <= prepared.test.timestamps.min()
    scaler = prepared.preprocessor.named_transformers_["numeric"].named_steps["scaler"]
    assert scaler.mean_[0] == pytest.approx(2.5)
    assert prepared.validation.features.shape[1] == prepared.train.features.shape[1]
    assert prepared.test.features.shape[1] == prepared.train.features.shape[1]


def test_preprocessing_imputes_missing_values() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": [f"2026-01-01T00:{minute:02d}:00Z" for minute in range(6)],
            "value": [1, "N/A", 3, 4, 5, 6],
            "category": ["a", None, "a", "b", "b", "c"],
            "label": ["benign", "benign", "attack", "benign", "attack", "attack"],
        }
    )

    prepared = prepare_frame(frame, config())

    assert not pd.isna(prepared.train.features).any()
    assert not pd.isna(prepared.validation.features).any()
    assert not pd.isna(prepared.test.features).any()


def test_preprocessing_rejects_missing_required_columns() -> None:
    with pytest.raises(ValueError, match="missing required columns: category"):
        prepare_frame(
            pd.DataFrame(
                {
                    "timestamp": ["2026-01-01T00:00:00Z"] * 3,
                    "value": [1, 2, 3],
                    "label": ["benign"] * 3,
                }
            ),
            config(),
        )
