from app.intelligence.common import event_id
from app.schemas.events import EventSeverity, NormalizedEventCreate
from app.schemas.workflow import (
    DetectionAgentRequest,
    DetectionAgentResult,
    DetectionFinding,
    FeatureSignal,
)

SEVERITY_SCORES = {
    EventSeverity.informational: 0.05,
    EventSeverity.low: 0.15,
    EventSeverity.medium: 0.35,
    EventSeverity.high: 0.65,
    EventSeverity.critical: 0.85,
}
ATTACK_MARKERS = (
    "attack",
    "credential",
    "exploit",
    "exfiltration",
    "intrusion",
    "lateral",
    "malware",
    "authentication_failure",
)


class DetectionAgent:
    """Versioned, deterministic online baseline behind the detection-agent contract."""

    model_name = "severity-anomaly-baseline"
    model_version = "1.0.0"

    @staticmethod
    def _attribute_anomaly(event: NormalizedEventCreate) -> float:
        raw_value = event.attributes.get("anomaly_score", 0.0)
        if isinstance(raw_value, int | float) and not isinstance(raw_value, bool):
            return min(1.0, max(0.0, float(raw_value)))
        return 0.0

    def _predict(self, event: NormalizedEventCreate) -> DetectionFinding:
        severity_score = SEVERITY_SCORES[event.severity]
        event_type_match = any(marker in event.event_type.lower() for marker in ATTACK_MARKERS)
        event_type_score = 0.15 if event_type_match else 0.0
        action_match = (event.action or "").lower() in {"blocked", "denied", "failed"}
        action_score = 0.05 if action_match else 0.0
        attribute_anomaly = self._attribute_anomaly(event)
        anomaly_contribution = 0.20 * attribute_anomaly
        confidence = round(
            min(1.0, severity_score + event_type_score + action_score + anomaly_contribution), 4
        )
        anomaly_score = round(max(attribute_anomaly, confidence), 4)
        if confidence >= 0.75:
            classification = "attack"
        elif confidence >= 0.4:
            classification = "suspicious"
        else:
            classification = "benign"

        signals = [
            FeatureSignal(
                name="severity",
                value=event.severity.value,
                contribution=severity_score,
                evidence=f"Mapped {event.severity.value} severity through the versioned baseline.",
            ),
            FeatureSignal(
                name="event_type",
                value=event.event_type,
                contribution=event_type_score,
                evidence=(
                    "Event type matched a documented attack marker."
                    if event_type_match
                    else "Event type did not match a documented attack marker."
                ),
            ),
            FeatureSignal(
                name="action",
                value=event.action or "missing",
                contribution=action_score,
                evidence=(
                    "Action indicates a blocked, denied, or failed attempt."
                    if action_match
                    else "Action added no baseline risk contribution."
                ),
            ),
        ]
        if attribute_anomaly:
            signals.append(
                FeatureSignal(
                    name="anomaly_score",
                    value=str(attribute_anomaly),
                    contribution=round(anomaly_contribution, 4),
                    evidence="Used the validated event anomaly_score attribute.",
                )
            )
        return DetectionFinding(
            event_id=event_id(event),
            classification=classification,
            confidence=confidence,
            anomaly_score=anomaly_score,
            model_name=self.model_name,
            model_version=self.model_version,
            important_features=sorted(
                signals, key=lambda item: (-abs(item.contribution), item.name)
            ),
        )

    def run(self, request: DetectionAgentRequest) -> DetectionAgentResult:
        return DetectionAgentResult(findings=[self._predict(event) for event in request.events])
