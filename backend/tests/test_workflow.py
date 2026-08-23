import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.agents import (
    CorrelationAgent,
    DetectionAgent,
    ExplainabilityAgent,
    ResponseAgent,
    RiskAgent,
    WorkflowCoordinator,
)
from app.main import app
from app.schemas.intelligence import AttackGraph
from app.schemas.workflow import (
    CorrelationAgentRequest,
    DetectionAgentRequest,
    ExplainabilityAgentRequest,
    ResponseAgentRequest,
    RiskAgentRequest,
    WorkflowRequest,
)

FIXTURE = Path(__file__).parent / "fixtures" / "phase5-workflow-v1.json"
client = TestClient(app)


def workflow_request() -> WorkflowRequest:
    return WorkflowRequest.model_validate(json.loads(FIXTURE.read_text(encoding="utf-8")))


def test_each_agent_accepts_its_contract_and_produces_structured_handoffs() -> None:
    workflow = workflow_request()
    detection = DetectionAgent().run(DetectionAgentRequest(events=workflow.events))
    assert [finding.classification for finding in detection.findings] == [
        "attack",
        "attack",
        "benign",
    ]

    correlation = CorrelationAgent().run(
        CorrelationAgentRequest(
            events=workflow.events,
            findings=detection.findings,
            window_minutes=workflow.window_minutes,
        )
    )
    assert len(correlation.incidents) == 1
    assert correlation.attack_graph.nodes

    risk = RiskAgent().run(
        RiskAgentRequest(
            events=workflow.events,
            findings=detection.findings,
            incidents=correlation.incidents,
            asset_criticality=workflow.asset_criticality,
            attack_stage=workflow.attack_stage,
            anomaly_level=workflow.anomaly_level,
            as_of=workflow.as_of,
        )
    )
    assert len(risk.assessments) == 2
    assert risk.assessments[0].risk.score >= risk.assessments[1].risk.score

    explanations = ExplainabilityAgent().run(
        ExplainabilityAgentRequest(
            findings=detection.findings,
            assessments=risk.assessments,
            attack_graph=correlation.attack_graph,
        )
    )
    assert all(item.important_features for item in explanations.explanations)
    assert all("do not prove causality" in item.limitations for item in explanations.explanations)

    response = ResponseAgent().run(
        ResponseAgentRequest(
            events=workflow.events,
            findings=detection.findings,
            assessments=risk.assessments,
            confirmed_malicious_ips=workflow.confirmed_malicious_ips,
            vulnerability_id=workflow.vulnerability_id,
        )
    )
    assert response.recommendations
    assert all(
        not bundle.recommendation.automatic_execution
        and bundle.recommendation.requires_human_approval
        for bundle in response.recommendations
    )


def test_coordinator_records_every_stage_and_keeps_human_as_final_approver() -> None:
    result = WorkflowCoordinator().run(workflow_request())

    assert result.status == "completed"
    assert [record.agent for record in result.audit_trail] == [
        "detection",
        "correlation",
        "risk",
        "explainability",
        "response",
    ]
    assert all(record.status == "completed" for record in result.audit_trail)
    assert all(record.input_digest for record in result.audit_trail)
    assert all(record.output_digest for record in result.audit_trail)
    assert result.human_approval.approval_status == "pending"
    assert result.human_approval.execution_permitted is False


class FailingCorrelationAgent(CorrelationAgent):
    def run(self, request: CorrelationAgentRequest):
        raise RuntimeError("simulated correlation outage")


def test_coordinator_isolates_correlation_failure_and_continues_safe_stages() -> None:
    result = WorkflowCoordinator(correlation=FailingCorrelationAgent()).run(workflow_request())

    assert result.status == "partial_failure"
    assert result.correlation is None
    assert result.risk is not None
    assert result.explainability is not None
    assert result.response is not None
    assert result.audit_trail[1].status == "failed"
    assert result.errors[0].agent == "correlation"
    assert result.human_approval.execution_permitted is False


class FailingDetectionAgent(DetectionAgent):
    def run(self, request: DetectionAgentRequest):
        raise RuntimeError("simulated model outage")


def test_detection_failure_stops_dependent_agents_without_unsafe_fallback() -> None:
    result = WorkflowCoordinator(detection=FailingDetectionAgent()).run(workflow_request())

    assert result.status == "failed"
    assert [record.status for record in result.audit_trail] == [
        "failed",
        "skipped",
        "skipped",
        "skipped",
        "skipped",
    ]
    assert result.response is None
    assert result.human_approval.execution_permitted is False


class FailingRiskAgent(RiskAgent):
    def run(self, request: RiskAgentRequest):
        raise RuntimeError("simulated risk outage")


def test_risk_failure_skips_response_but_preserves_explanation() -> None:
    result = WorkflowCoordinator(risk=FailingRiskAgent()).run(workflow_request())

    assert result.status == "partial_failure"
    assert result.risk is None
    assert result.explainability is not None
    assert result.response is None
    assert result.audit_trail[2].status == "failed"
    assert result.audit_trail[4].status == "skipped"


class FailingExplainabilityAgent(ExplainabilityAgent):
    def run(self, request: ExplainabilityAgentRequest):
        raise RuntimeError("simulated explanation outage")


class FailingResponseAgent(ResponseAgent):
    def run(self, request: ResponseAgentRequest):
        raise RuntimeError("simulated response outage")


def test_late_stage_failures_preserve_prior_analysis() -> None:
    explanation_failure = WorkflowCoordinator(
        explainability=FailingExplainabilityAgent()
    ).run(workflow_request())
    assert explanation_failure.status == "partial_failure"
    assert explanation_failure.explainability is None
    assert explanation_failure.response is not None

    response_failure = WorkflowCoordinator(response=FailingResponseAgent()).run(workflow_request())
    assert response_failure.status == "partial_failure"
    assert response_failure.risk is not None
    assert response_failure.explainability is not None
    assert response_failure.response is None


def test_workflow_and_component_apis_expose_the_phase5_contracts() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    detection_response = client.post(
        "/api/v1/agents/detection/run", json={"events": payload["events"]}
    )
    assert detection_response.status_code == 200
    assert detection_response.json()["contract_version"] == "phase5-v1"

    workflow_response = client.post("/api/v1/workflows/analyze", json=payload)
    assert workflow_response.status_code == 200
    body = workflow_response.json()
    assert body["status"] == "completed"
    assert body["human_approval"]["execution_permitted"] is False
    assert len(body["audit_trail"]) == 5


def test_explainability_contract_allows_empty_graph_after_correlation_failure() -> None:
    workflow = workflow_request()
    detection = DetectionAgent().run(DetectionAgentRequest(events=workflow.events))
    result = ExplainabilityAgent().run(
        ExplainabilityAgentRequest(
            findings=detection.findings,
            assessments=[],
            attack_graph=AttackGraph(nodes=[], edges=[]),
        )
    )
    assert result.explanations
    assert all(not item.supporting_edge_ids for item in result.explanations)
