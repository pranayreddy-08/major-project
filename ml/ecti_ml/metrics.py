from dataclasses import asdict, dataclass

import numpy as np
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, roc_auc_score


@dataclass(frozen=True)
class BinaryMetrics:
    precision: float
    recall: float
    f1: float
    roc_auc: float
    false_positive_rate: float
    inference_time_ms: float
    samples: int

    def as_dict(self) -> dict[str, float | int]:
        return asdict(self)


def evaluate_binary(
    labels: np.ndarray,
    probabilities: np.ndarray,
    *,
    inference_time_ms: float = 0.0,
    threshold: float = 0.5,
) -> BinaryMetrics:
    labels = np.asarray(labels, dtype=int)
    probabilities = np.asarray(probabilities, dtype=float)
    predictions = (probabilities >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels,
        predictions,
        average="binary",
        zero_division=0,
    )
    matrix = confusion_matrix(labels, predictions, labels=[0, 1])
    true_negative, false_positive, _, _ = matrix.ravel()
    negative_count = true_negative + false_positive
    false_positive_rate = false_positive / negative_count if negative_count else 0.0
    roc_auc = roc_auc_score(labels, probabilities) if len(set(labels.tolist())) > 1 else 0.5
    return BinaryMetrics(
        precision=float(precision),
        recall=float(recall),
        f1=float(f1),
        roc_auc=float(roc_auc),
        false_positive_rate=float(false_positive_rate),
        inference_time_ms=float(inference_time_ms),
        samples=len(labels),
    )
