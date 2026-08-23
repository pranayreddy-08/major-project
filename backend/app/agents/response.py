from app.intelligence.common import event_id
from app.intelligence.response import recommend_actions
from app.schemas.intelligence import ResponseContext
from app.schemas.workflow import (
    RecommendationBundle,
    ResponseAgentRequest,
    ResponseAgentResult,
)


class ResponseAgent:
    def run(self, request: ResponseAgentRequest) -> ResponseAgentResult:
        event_lookup = {event_id(event): event for event in request.events}
        finding_lookup = {finding.event_id: finding for finding in request.findings}
        confirmed_ips = {str(address) for address in request.confirmed_malicious_ips}
        bundles: dict[tuple[str, str], RecommendationBundle] = {}

        for assessment in request.assessments:
            event = event_lookup.get(assessment.event_id)
            finding = finding_lookup.get(assessment.event_id)
            if event is None or finding is None:
                raise ValueError(
                    f"risk assessment references unknown event or finding: {assessment.event_id}"
                )
            source_ip = str(event.source_ip) if event.source_ip else None
            recommendations = recommend_actions(
                ResponseContext(
                    risk_score=assessment.risk.score,
                    confidence=finding.confidence,
                    event_type=event.event_type,
                    host=event.host,
                    user=event.user,
                    source_ip=event.source_ip,
                    malicious_ip_confirmed=source_ip in confirmed_ips,
                    vulnerability_id=request.vulnerability_id,
                )
            )
            for recommendation in recommendations:
                key = (recommendation.action, recommendation.target)
                existing = bundles.get(key)
                if existing is None:
                    bundles[key] = RecommendationBundle(
                        recommendation=recommendation,
                        supporting_event_ids=[assessment.event_id],
                    )
                else:
                    existing.supporting_event_ids = sorted(
                        {*existing.supporting_event_ids, assessment.event_id}
                    )

        return ResponseAgentResult(
            recommendations=sorted(
                bundles.values(),
                key=lambda item: (
                    item.recommendation.action,
                    item.recommendation.target,
                ),
            )
        )
