from dataclasses import asdict, dataclass

import numpy as np
import shap
from sklearn.linear_model import LogisticRegression


@dataclass(frozen=True)
class FeatureContribution:
    feature: str
    value: float
    shap_value: float


@dataclass(frozen=True)
class PredictionExplanation:
    method: str
    predicted_probability: float
    base_value: float
    contributions: tuple[FeatureContribution, ...]
    limitations: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def explain_logistic_prediction(
    model: LogisticRegression,
    background: np.ndarray,
    sample: np.ndarray,
    feature_names: tuple[str, ...],
    *,
    top_k: int = 8,
) -> PredictionExplanation:
    sample = np.asarray(sample).reshape(1, -1)
    explainer = shap.LinearExplainer(model, np.asarray(background))
    explanation = explainer(sample)
    shap_values = np.asarray(explanation.values).reshape(-1)
    base_value = float(np.asarray(explanation.base_values).reshape(-1)[0])
    contributions = sorted(
        (
            FeatureContribution(
                feature=feature,
                value=float(value),
                shap_value=float(impact),
            )
            for feature, value, impact in zip(
                feature_names,
                sample.reshape(-1),
                shap_values,
                strict=True,
            )
        ),
        key=lambda item: (-abs(item.shap_value), item.feature),
    )[:top_k]
    return PredictionExplanation(
        method="shap-linear",
        predicted_probability=float(model.predict_proba(sample)[0, 1]),
        base_value=base_value,
        contributions=tuple(contributions),
        limitations=(
            "SHAP describes this model's behavior relative to the training background; it does "
            "not establish causality or guarantee correctness."
        ),
    )
