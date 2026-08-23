from math import pow

from app.schemas.intelligence import RiskInput, RiskResult

FORMULA_VERSION = "risk-v1"
WEIGHTS = {
    "threat_confidence": 0.35,
    "asset_criticality": 0.25,
    "attack_stage": 0.15,
    "anomaly_level": 0.15,
    "recency": 0.10,
}
RECENCY_HALF_LIFE_HOURS = 24.0


def calculate_risk(value: RiskInput) -> RiskResult:
    age_seconds = max(0.0, (value.as_of - value.observed_at).total_seconds())
    age_hours = age_seconds / 3600
    recency = pow(0.5, age_hours / RECENCY_HALF_LIFE_HOURS)
    inputs = {
        "threat_confidence": value.threat_confidence,
        "asset_criticality": value.asset_criticality,
        "attack_stage": value.attack_stage,
        "anomaly_level": value.anomaly_level,
        "recency": recency,
    }
    components = {
        name: round(100 * WEIGHTS[name] * component, 4) for name, component in inputs.items()
    }
    score = round(min(100.0, max(0.0, sum(components.values()))), 2)
    if score >= 85:
        level = "critical"
    elif score >= 65:
        level = "high"
    elif score >= 35:
        level = "medium"
    else:
        level = "low"
    return RiskResult(
        score=score,
        level=level,
        components=components,
        formula_version=FORMULA_VERSION,
    )
