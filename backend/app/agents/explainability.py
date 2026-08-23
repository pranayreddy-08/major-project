from app.schemas.workflow import (
    ExplainabilityAgentRequest,
    ExplainabilityAgentResult,
    WorkflowExplanation,
)


class ExplainabilityAgent:
    def run(self, request: ExplainabilityAgentRequest) -> ExplainabilityAgentResult:
        assessment_lookup = {assessment.event_id: assessment for assessment in request.assessments}
        explanations: list[WorkflowExplanation] = []
        for finding in request.findings:
            if finding.classification == "benign":
                continue
            assessment = assessment_lookup.get(finding.event_id)
            supporting_edges = sorted(
                (edge for edge in request.attack_graph.edges if edge.event_id == finding.event_id),
                key=lambda edge: edge.id,
            )
            supporting_events = sorted({edge.event_id for edge in supporting_edges})
            leading = finding.important_features[0] if finding.important_features else None
            reason = (
                f" The strongest baseline signal was {leading.name}={leading.value}."
                if leading
                else ""
            )
            explanations.append(
                WorkflowExplanation(
                    event_id=finding.event_id,
                    summary=(
                        f"The detection agent classified this event as {finding.classification} "
                        f"with {finding.confidence:.1%} confidence.{reason}"
                    ),
                    confidence=finding.confidence,
                    risk_score=assessment.risk.score if assessment else None,
                    important_features=finding.important_features,
                    supporting_edge_ids=[edge.id for edge in supporting_edges],
                    supporting_event_ids=supporting_events,
                    limitations=(
                        "Feature contributions and deterministic graph relationships describe the "
                        "prototype's decision path; they do not prove causality, malicious intent, "
                        "or real-world model correctness."
                    ),
                )
            )
        return ExplainabilityAgentResult(
            explanations=sorted(explanations, key=lambda item: item.event_id)
        )
