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
