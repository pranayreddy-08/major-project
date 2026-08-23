from dataclasses import dataclass
from time import perf_counter

import numpy as np
from sklearn.linear_model import LogisticRegression

from ecti_ml.metrics import BinaryMetrics, evaluate_binary
from ecti_ml.preprocessing import PreparedDataset


@dataclass(frozen=True)
class BaselineResult:
    model: LogisticRegression
    validation: BinaryMetrics
    test: BinaryMetrics
    validation_probabilities: np.ndarray
    test_probabilities: np.ndarray


def _labels(values: np.ndarray, positive_label: str) -> np.ndarray:
    return (np.asarray(values) == positive_label).astype(int)


def train_logistic_baseline(
    dataset: PreparedDataset,
    *,
    positive_label: str = "attack",
    random_state: int = 42,
    decision_threshold: float = 0.5,
) -> BaselineResult:
    model = LogisticRegression(
        class_weight="balanced",
        max_iter=1000,
        random_state=random_state,
    )
    model.fit(dataset.train.features, _labels(dataset.train.labels, positive_label))

    start = perf_counter()
    validation_probabilities = model.predict_proba(dataset.validation.features)[:, 1]
    validation_time = (perf_counter() - start) * 1000
    start = perf_counter()
    test_probabilities = model.predict_proba(dataset.test.features)[:, 1]
    test_time = (perf_counter() - start) * 1000

    return BaselineResult(
        model=model,
        validation=evaluate_binary(
            _labels(dataset.validation.labels, positive_label),
            validation_probabilities,
            inference_time_ms=validation_time,
            threshold=decision_threshold,
        ),
        test=evaluate_binary(
            _labels(dataset.test.labels, positive_label),
            test_probabilities,
            inference_time_ms=test_time,
            threshold=decision_threshold,
        ),
        validation_probabilities=validation_probabilities,
        test_probabilities=test_probabilities,
    )
