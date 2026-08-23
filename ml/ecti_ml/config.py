import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PreprocessingConfig:
    config_version: str
    dataset_version: str
    timestamp_column: str
    label_column: str
    numeric_columns: tuple[str, ...]
    categorical_columns: tuple[str, ...]
    train_fraction: float
    validation_fraction: float
    test_fraction: float

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "PreprocessingConfig":
        config = cls(
            config_version=str(value["config_version"]),
            dataset_version=str(value["dataset_version"]),
            timestamp_column=str(value["timestamp_column"]),
            label_column=str(value["label_column"]),
            numeric_columns=tuple(value["numeric_columns"]),
            categorical_columns=tuple(value["categorical_columns"]),
            train_fraction=float(value["split"]["train"]),
            validation_fraction=float(value["split"]["validation"]),
            test_fraction=float(value["split"]["test"]),
        )
        config.validate()
        return config

    @classmethod
    def from_json(cls, path: str | Path) -> "PreprocessingConfig":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def validate(self) -> None:
        fractions = (self.train_fraction, self.validation_fraction, self.test_fraction)
        if any(fraction <= 0 for fraction in fractions):
            raise ValueError("all split fractions must be positive")
        if abs(sum(fractions) - 1.0) > 1e-9:
            raise ValueError("split fractions must sum to 1")
        if not self.numeric_columns and not self.categorical_columns:
            raise ValueError("at least one feature column is required")
        if set(self.numeric_columns) & set(self.categorical_columns):
            raise ValueError("numeric and categorical columns must not overlap")
