from datetime import timedelta

from app.intelligence.common import event_id
from app.intelligence.correlation import correlate_events
from app.intelligence.graph import build_attack_graph
from app.schemas.workflow import CorrelationAgentRequest, CorrelationAgentResult


class CorrelationAgent:
    def run(self, request: CorrelationAgentRequest) -> CorrelationAgentResult:
        event_lookup = {event_id(event): event for event in request.events}
        unknown = sorted(
            finding.event_id for finding in request.findings if finding.event_id not in event_lookup
        )
        if unknown:
            raise ValueError(f"findings reference unknown events: {', '.join(unknown)}")
        selected_ids = {
            finding.event_id
            for finding in request.findings
            if finding.classification != "benign"
        }
        selected_events = [
            event for event in request.events if event_id(event) in selected_ids
        ]
        return CorrelationAgentResult(
            incidents=correlate_events(
                selected_events, window=timedelta(minutes=request.window_minutes)
            ),
            attack_graph=build_attack_graph(selected_events),
        )
