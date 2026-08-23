import hashlib
import json
from collections.abc import Callable
from datetime import datetime, timezone
from typing import TypeVar

from pydantic import BaseModel

from app.agents.correlation import CorrelationAgent
from app.agents.detection import DetectionAgent
from app.agents.explainability import ExplainabilityAgent
from app.agents.response import ResponseAgent
from app.agents.risk import RiskAgent
from app.intelligence.common import stable_id
from app.schemas.intelligence import AttackGraph
from app.schemas.workflow import (
    AgentAuditRecord,
    CorrelationAgentRequest,
    DetectionAgentRequest,
    DetectionAgentResult,
    ExplainabilityAgentRequest,
    ResponseAgentRequest,
    RiskAgentRequest,
    WorkflowError,
    WorkflowRequest,
    WorkflowResult,
)

ResultT = TypeVar("ResultT", bound=BaseModel)


def _digest(value: BaseModel) -> str:
    payload = json.dumps(
        value.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class WorkflowCoordinator:
    """Runs bounded agents in order and returns a complete, non-executing audit envelope."""

    def __init__(
        self,
        *,
        detection: DetectionAgent | None = None,
        correlation: CorrelationAgent | None = None,
        risk: RiskAgent | None = None,
        explainability: ExplainabilityAgent | None = None,
        response: ResponseAgent | None = None,
    ) -> None:
        self.detection = detection or DetectionAgent()
        self.correlation = correlation or CorrelationAgent()
        self.risk = risk or RiskAgent()
        self.explainability = explainability or ExplainabilityAgent()
        self.response = response or ResponseAgent()

    @staticmethod
    def _invoke(
        sequence: int,
        agent: str,
        request: BaseModel,
        operation: Callable[[BaseModel], ResultT],
    ) -> tuple[ResultT | None, AgentAuditRecord, WorkflowError | None]:
        started_at = datetime.now(timezone.utc)
        try:
            result = operation(request)
        except Exception as exc:  # coordinator converts bounded agent failures into data
            completed_at = datetime.now(timezone.utc)
            safe_message = str(exc).replace("\n", " ")[:300] or "agent execution failed"
            return (
                None,
                AgentAuditRecord(
                    sequence=sequence,
                    agent=agent,
                    status="failed",
                    started_at=started_at,
                    completed_at=completed_at,
                    input_digest=_digest(request),
                    detail=f"{type(exc).__name__}: {safe_message}",
                ),
                WorkflowError(
                    agent=agent,
                    error_type=type(exc).__name__,
                    message=safe_message,
                ),
            )
        completed_at = datetime.now(timezone.utc)
        return (
            result,
            AgentAuditRecord(
                sequence=sequence,
                agent=agent,
                status="completed",
                started_at=started_at,
                completed_at=completed_at,
                input_digest=_digest(request),
                output_digest=_digest(result),
                detail="Structured handoff completed.",
            ),
            None,
        )

    @staticmethod
    def _skipped(sequence: int, agent: str, request: BaseModel, reason: str) -> AgentAuditRecord:
        timestamp = datetime.now(timezone.utc)
        return AgentAuditRecord(
            sequence=sequence,
            agent=agent,
            status="skipped",
            started_at=timestamp,
            completed_at=timestamp,
            input_digest=_digest(request),
            detail=reason,
        )

    def run(self, request: WorkflowRequest) -> WorkflowResult:
        request_digest = _digest(request)
        workflow_id = stable_id("workflow", request_digest)
        audit: list[AgentAuditRecord] = []
        errors: list[WorkflowError] = []

        detection_request = DetectionAgentRequest(events=request.events)
        detection, record, error = self._invoke(
            1, "detection", detection_request, self.detection.run
        )
        audit.append(record)
        if error:
            errors.append(error)

        if detection is None:
            empty_findings = DetectionAgentResult(findings=[])
            correlation_request = CorrelationAgentRequest(
                events=request.events,
                findings=empty_findings.findings,
                window_minutes=request.window_minutes,
            )
            risk_request = RiskAgentRequest(
                events=request.events,
                findings=[],
                incidents=[],
                asset_criticality=request.asset_criticality,
                attack_stage=request.attack_stage,
                anomaly_level=request.anomaly_level,
                as_of=request.as_of,
            )
            explainability_request = ExplainabilityAgentRequest(
                findings=[], assessments=[], attack_graph=AttackGraph(nodes=[], edges=[])
            )
            response_request = ResponseAgentRequest(
                events=request.events,
                findings=[],
                assessments=[],
                confirmed_malicious_ips=request.confirmed_malicious_ips,
                vulnerability_id=request.vulnerability_id,
            )
            for sequence, agent, skipped_request in (
                (2, "correlation", correlation_request),
                (3, "risk", risk_request),
                (4, "explainability", explainability_request),
                (5, "response", response_request),
            ):
                audit.append(
                    self._skipped(
                        sequence,
                        agent,
                        skipped_request,
                        "Skipped because the detection handoff failed.",
                    )
                )
            return WorkflowResult(
                workflow_id=workflow_id,
                status="failed",
                audit_trail=audit,
                errors=errors,
            )

        correlation_request = CorrelationAgentRequest(
            events=request.events,
            findings=detection.findings,
            window_minutes=request.window_minutes,
        )
        correlation, record, error = self._invoke(
            2, "correlation", correlation_request, self.correlation.run
        )
        audit.append(record)
        if error:
            errors.append(error)
        incidents = correlation.incidents if correlation else []
        attack_graph = correlation.attack_graph if correlation else AttackGraph(nodes=[], edges=[])

        risk_request = RiskAgentRequest(
            events=request.events,
            findings=detection.findings,
            incidents=incidents,
            asset_criticality=request.asset_criticality,
            attack_stage=request.attack_stage,
            anomaly_level=request.anomaly_level,
            as_of=request.as_of,
        )
        risk, record, error = self._invoke(3, "risk", risk_request, self.risk.run)
        audit.append(record)
        if error:
            errors.append(error)

        explainability_request = ExplainabilityAgentRequest(
            findings=detection.findings,
            assessments=risk.assessments if risk else [],
            attack_graph=attack_graph,
        )
        explainability, record, error = self._invoke(
            4, "explainability", explainability_request, self.explainability.run
        )
        audit.append(record)
        if error:
            errors.append(error)

        response_request = ResponseAgentRequest(
            events=request.events,
            findings=detection.findings,
            assessments=risk.assessments if risk else [],
            confirmed_malicious_ips=request.confirmed_malicious_ips,
            vulnerability_id=request.vulnerability_id,
        )
        if risk is None:
            response = None
            audit.append(
                self._skipped(
                    5,
                    "response",
                    response_request,
                    "Skipped because the risk handoff failed.",
                )
            )
        else:
            response, record, error = self._invoke(
                5, "response", response_request, self.response.run
            )
            audit.append(record)
            if error:
                errors.append(error)

        return WorkflowResult(
            workflow_id=workflow_id,
            status="completed" if not errors else "partial_failure",
            detection=detection,
            correlation=correlation,
            risk=risk,
            explainability=explainability,
            response=response,
            audit_trail=audit,
            errors=errors,
        )
