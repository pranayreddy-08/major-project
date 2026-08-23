from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ecti_ml.config import PreprocessingConfig

MISSING_MARKERS = frozenset({"", "-", "n/a", "null", "none", "nan"})


def _missing_to_nan(value: object) -> object:
    if isinstance(value, str) and value.strip().lower() in MISSING_MARKERS:
        return np.nan
    return value


@dataclass(frozen=True)
class PreparedSplit:
    features: np.ndarray
    labels: np.ndarray
    timestamps: pd.Series


@dataclass(frozen=True)
class PreparedDataset:
    train: PreparedSplit
    validation: PreparedSplit
    test: PreparedSplit
    feature_names: tuple[str, ...]
    dataset_version: str
    config_version: str
    preprocessor: ColumnTransformer


def _clean_and_sort(frame: pd.DataFrame, config: PreprocessingConfig) -> pd.DataFrame:
    required = {
        config.timestamp_column,
        config.label_column,
        *config.numeric_columns,
        *config.categorical_columns,
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")

    cleaned = frame.copy()
    for column in cleaned.columns:
        cleaned[column] = cleaned[column].map(_missing_to_nan)
    cleaned = cleaned.drop_duplicates()
    for column in config.numeric_columns:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
    for column in config.categorical_columns:
        cleaned[column] = cleaned[column].where(cleaned[column].notna(), np.nan)
    cleaned[config.timestamp_column] = pd.to_datetime(
        cleaned[config.timestamp_column], errors="raise", utc=True
    )
    cleaned = cleaned.dropna(subset=[config.timestamp_column, config.label_column])
    return cleaned.sort_values(config.timestamp_column, kind="stable").reset_index(drop=True)


def temporal_split(
    frame: pd.DataFrame, config: PreprocessingConfig
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    row_count = len(frame)
    if row_count < 3:
        raise ValueError("at least three valid rows are required for temporal splitting")

    train_end = max(1, int(row_count * config.train_fraction))
    validation_size = max(1, int(row_count * config.validation_fraction))
    validation_end = min(row_count - 1, train_end + validation_size)
    if validation_end <= train_end:
        train_end = validation_end - 1

    train = frame.iloc[:train_end].copy()
    validation = frame.iloc[train_end:validation_end].copy()
    test = frame.iloc[validation_end:].copy()
    if train.empty or validation.empty or test.empty:
        raise ValueError("split fractions produced an empty dataset partition")
    return train, validation, test


def _build_preprocessor(config: PreprocessingConfig) -> ColumnTransformer:
    numeric = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="constant", fill_value="missing", keep_empty_features=True),
            ),
            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric, list(config.numeric_columns)),
            ("categorical", categorical, list(config.categorical_columns)),
        ],
        verbose_feature_names_out=False,
    )


def _transform_split(
    frame: pd.DataFrame,
    config: PreprocessingConfig,
    preprocessor: ColumnTransformer,
) -> PreparedSplit:
    feature_columns = [*config.numeric_columns, *config.categorical_columns]
    return PreparedSplit(
        features=np.asarray(preprocessor.transform(frame[feature_columns])),
        labels=frame[config.label_column].to_numpy(copy=True),
        timestamps=frame[config.timestamp_column].copy(),
    )


def prepare_frame(frame: pd.DataFrame, config: PreprocessingConfig) -> PreparedDataset:
    """Split by event time, then fit imputers/encoders/scalers on training rows only."""
    config.validate()
    cleaned = _clean_and_sort(frame, config)
    train_frame, validation_frame, test_frame = temporal_split(cleaned, config)
    feature_columns = [*config.numeric_columns, *config.categorical_columns]
    preprocessor = _build_preprocessor(config)
    preprocessor.fit(train_frame[feature_columns])

    return PreparedDataset(
        train=_transform_split(train_frame, config, preprocessor),
        validation=_transform_split(validation_frame, config, preprocessor),
        test=_transform_split(test_frame, config, preprocessor),
        feature_names=tuple(preprocessor.get_feature_names_out()),
        dataset_version=config.dataset_version,
        config_version=config.config_version,
        preprocessor=preprocessor,
    )


def prepare_csv(path: str, config: PreprocessingConfig) -> PreparedDataset:
    return prepare_frame(pd.read_csv(path), config)
