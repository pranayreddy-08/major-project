from app.intelligence.common import event_id
from app.intelligence.risk import calculate_risk
from app.schemas.intelligence import RiskInput
from app.schemas.workflow import RiskAgentRequest, RiskAgentResult, RiskAssessment


class RiskAgent:
    def run(self, request: RiskAgentRequest) -> RiskAgentResult:
        event_lookup = {event_id(event): event for event in request.events}
        assessments: list[RiskAssessment] = []
        for finding in request.findings:
            if finding.classification == "benign":
                continue
            event = event_lookup.get(finding.event_id)
            if event is None:
                raise ValueError(f"finding references unknown event: {finding.event_id}")
            incident_ids = sorted(
                incident.id
                for incident in request.incidents
                if finding.event_id in incident.event_ids
            )
            risk = calculate_risk(
                RiskInput(
                    threat_confidence=finding.confidence,
                    asset_criticality=request.asset_criticality,
                    attack_stage=request.attack_stage,
                    anomaly_level=max(request.anomaly_level, finding.anomaly_score),
                    observed_at=event.timestamp,
                    as_of=request.as_of,
                )
            )
            assessments.append(
                RiskAssessment(
                    event_id=finding.event_id,
                    incident_ids=incident_ids,
                    risk=risk,
                )
            )
        return RiskAgentResult(
            assessments=sorted(
                assessments, key=lambda item: (-item.risk.score, item.event_id)
            )
        )
