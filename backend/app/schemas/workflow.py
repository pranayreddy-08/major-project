from datetime import datetime
from ipaddress import IPv4Address, IPv6Address
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.events import NormalizedEventCreate
from app.schemas.intelligence import (
    AttackGraph,
    CorrelatedIncident,
    ResponseRecommendation,
    RiskResult,
)


class FeatureSignal(BaseModel):
    name: str
    value: str
    contribution: float
    evidence: str


class DetectionFinding(BaseModel):
    event_id: str
    classification: Literal["benign", "suspicious", "attack"]
    confidence: float = Field(ge=0, le=1)
    anomaly_score: float = Field(ge=0, le=1)
    model_name: str
    model_version: str
    important_features: list[FeatureSignal]


class DetectionAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[NormalizedEventCreate] = Field(min_length=1)


class DetectionAgentResult(BaseModel):
    agent: Literal["detection"] = "detection"
    contract_version: Literal["phase5-v1"] = "phase5-v1"
    findings: list[DetectionFinding]


class CorrelationAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[NormalizedEventCreate] = Field(min_length=1)
    findings: list[DetectionFinding]
    window_minutes: int = Field(default=15, ge=1, le=1440)


class CorrelationAgentResult(BaseModel):
    agent: Literal["correlation"] = "correlation"
    contract_version: Literal["phase5-v1"] = "phase5-v1"
    incidents: list[CorrelatedIncident]
    attack_graph: AttackGraph


class RiskAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[NormalizedEventCreate] = Field(min_length=1)
    findings: list[DetectionFinding]
    incidents: list[CorrelatedIncident]
    asset_criticality: float = Field(default=0.5, ge=0, le=1)
    attack_stage: float = Field(default=0.5, ge=0, le=1)
    anomaly_level: float = Field(default=0.5, ge=0, le=1)
    as_of: datetime

    @field_validator("as_of")
    @classmethod
    def as_of_must_include_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("as_of must include a timezone")
        return value


class RiskAssessment(BaseModel):
    event_id: str
    incident_ids: list[str]
    risk: RiskResult


class RiskAgentResult(BaseModel):
    agent: Literal["risk"] = "risk"
    contract_version: Literal["phase5-v1"] = "phase5-v1"
    assessments: list[RiskAssessment]


class ExplainabilityAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    findings: list[DetectionFinding]
    assessments: list[RiskAssessment]
    attack_graph: AttackGraph


class WorkflowExplanation(BaseModel):
    event_id: str
    summary: str
    confidence: float = Field(ge=0, le=1)
    risk_score: float | None = Field(default=None, ge=0, le=100)
    important_features: list[FeatureSignal]
    supporting_edge_ids: list[str]
    supporting_event_ids: list[str]
    limitations: str


class ExplainabilityAgentResult(BaseModel):
    agent: Literal["explainability"] = "explainability"
    contract_version: Literal["phase5-v1"] = "phase5-v1"
    explanations: list[WorkflowExplanation]


class ResponseAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[NormalizedEventCreate] = Field(min_length=1)
    findings: list[DetectionFinding]
    assessments: list[RiskAssessment]
    confirmed_malicious_ips: list[IPv4Address | IPv6Address] = Field(default_factory=list)
    vulnerability_id: str | None = Field(default=None, max_length=100)


class RecommendationBundle(BaseModel):
    recommendation: ResponseRecommendation
    supporting_event_ids: list[str]


class ResponseAgentResult(BaseModel):
    agent: Literal["response"] = "response"
    contract_version: Literal["phase5-v1"] = "phase5-v1"
    recommendations: list[RecommendationBundle]


class WorkflowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[NormalizedEventCreate] = Field(min_length=1)
    window_minutes: int = Field(default=15, ge=1, le=1440)
    asset_criticality: float = Field(default=0.5, ge=0, le=1)
    attack_stage: float = Field(default=0.5, ge=0, le=1)
    anomaly_level: float = Field(default=0.5, ge=0, le=1)
    as_of: datetime
    confirmed_malicious_ips: list[IPv4Address | IPv6Address] = Field(default_factory=list)
    vulnerability_id: str | None = Field(default=None, max_length=100)

    @field_validator("as_of")
    @classmethod
    def workflow_as_of_must_include_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("as_of must include a timezone")
        return value


class AgentAuditRecord(BaseModel):
    sequence: int = Field(ge=1)
    agent: Literal["detection", "correlation", "risk", "explainability", "response"]
    status: Literal["completed", "failed", "skipped"]
    started_at: datetime
    completed_at: datetime
    input_digest: str
    output_digest: str | None = None
    detail: str


class WorkflowError(BaseModel):
    agent: str
    error_type: str
    message: str


class HumanApprovalGate(BaseModel):
    required: Literal[True] = True
    approval_status: Literal["pending"] = "pending"
    approved_by: None = None
    approved_at: None = None
    execution_permitted: Literal[False] = False


class WorkflowResult(BaseModel):
    workflow_id: str
    contract_version: Literal["phase5-v1"] = "phase5-v1"
    status: Literal["completed", "partial_failure", "failed"]
    detection: DetectionAgentResult | None = None
    correlation: CorrelationAgentResult | None = None
    risk: RiskAgentResult | None = None
    explainability: ExplainabilityAgentResult | None = None
    response: ResponseAgentResult | None = None
    audit_trail: list[AgentAuditRecord]
    errors: list[WorkflowError]
    human_approval: HumanApprovalGate = Field(default_factory=HumanApprovalGate)
