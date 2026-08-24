from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.entities import AlertStatus, IncidentStatus, Severity, UserRole
from app.schemas.events import NormalizedEventCreate
from app.schemas.intelligence import AttackGraph, ResponseRecommendation
from app.schemas.workflow import WorkflowRequest, WorkflowResult


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(gt=0)


class SetupStatus(BaseModel):
    setup_required: bool


class InitialAdministratorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=12, max_length=128)


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    full_name: str
    role: UserRole
    active: bool


class StoredEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    timestamp: datetime
    source_ip: str | None
    destination_ip: str | None
    user: str | None
    host: str | None
    protocol: str | None
    action: str | None
    severity: Severity
    log_source: str
    event_type: str
    attributes: dict[str, Any]


class EventIngestRequest(BaseModel):
    event: NormalizedEventCreate


class AlertSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    normalized_event_id: UUID | None
    incident_id: UUID | None
    alert_type: str
    title: str
    description: str | None
    severity: Severity
    confidence: float
    status: AlertStatus
    created_at: datetime


class IncidentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    status: IncidentStatus
    severity: Severity
    risk_score: float
    created_at: datetime
    updated_at: datetime


class ExplanationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    alert_id: UUID
    method: str
    summary: str
    evidence: dict[str, Any]
    limitations: str | None
    created_at: datetime


class RecommendationRead(BaseModel):
    alert_id: UUID
    recommendations: list[ResponseRecommendation]


class FeedbackCreate(BaseModel):
    alert_id: UUID | None = None
    incident_id: UUID | None = None
    verdict: Literal["confirmed", "dismissed", "needs_review"]
    comment: str | None = Field(default=None, max_length=2000)


class FeedbackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    alert_id: UUID | None
    incident_id: UUID | None
    analyst: str
    verdict: str
    comment: str | None
    created_at: datetime


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_username: str
    action: str
    resource_type: str
    resource_id: str | None
    detail: dict[str, Any]
    ip_address: str | None
    created_at: datetime


class SeverityCount(BaseModel):
    severity: Severity
    count: int = Field(ge=0)


class DashboardOverview(BaseModel):
    open_alerts: int = Field(ge=0)
    active_incidents: int = Field(ge=0)
    critical_alerts: int = Field(ge=0)
    monitored_events: int = Field(ge=0)
    severity_distribution: list[SeverityCount]
    recent_alerts: list[AlertSummary]
    model_status: Literal["operational", "degraded"]
    model_name: str
    model_version: str


class WorkflowAgentStep(BaseModel):
    sequence: int = Field(ge=1)
    agent: str
    status: Literal["completed", "failed", "skipped"]
    started_at: datetime
    completed_at: datetime
    duration_ms: float = Field(ge=0)
    detail: str
    input_digest: str
    output_digest: str | None = None


class WorkflowRunSummary(BaseModel):
    workflow_id: str
    status: Literal["completed", "partial_failure", "failed"]
    actor: str
    created_at: datetime
    event_count: int = Field(ge=0)
    alert_count: int = Field(ge=0)
    persisted: bool
    detection_model: str
    detection_model_version: str
    steps: list[WorkflowAgentStep]
    human_approval_required: Literal[True] = True
    execution_permitted: Literal[False] = False


class ModelMetrics(BaseModel):
    precision: float = Field(ge=0, le=1)
    recall: float = Field(ge=0, le=1)
    f1: float = Field(ge=0, le=1)
    roc_auc: float = Field(ge=0, le=1)
    samples: int = Field(ge=1)


class ModelProfile(BaseModel):
    id: str
    name: str
    version: str
    kind: Literal["deterministic_baseline", "logistic_regression", "graph_neural_network"]
    deployment: Literal["runtime", "evaluated_offline"]
    purpose: str
    architecture: str
    metrics: ModelMetrics | None = None


class ModelCatalog(BaseModel):
    experiment_version: str
    dataset_version: str
    models: list[ModelProfile]
    limitations: list[str]


class ThreatScenarioRead(BaseModel):
    id: str
    title: str
    category: str
    technique: str
    description: str
    expected_classification: Literal["attack", "suspicious", "benign"]
    severity: Severity
    event_count: int = Field(ge=1)
    signals: list[str]
    learning_points: list[str]


class IncidentDetail(BaseModel):
    incident: IncidentSummary
    alerts: list[AlertSummary]
    graph: AttackGraph


class AnalysisRunRequest(WorkflowRequest):
    persist: bool = True


class AnalysisRunResult(BaseModel):
    workflow: WorkflowResult
    stored_event_ids: list[UUID]
    stored_alert_ids: list[UUID]
