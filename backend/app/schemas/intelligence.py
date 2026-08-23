from datetime import datetime
from ipaddress import IPv4Address, IPv6Address
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.events import MAX_EVENT_BATCH, NormalizedEventCreate


class CorrelationBuildRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[NormalizedEventCreate] = Field(min_length=1, max_length=MAX_EVENT_BATCH)
    window_minutes: int = Field(default=15, ge=1, le=1440)


class CorrelationLink(BaseModel):
    source_event_id: str
    target_event_id: str
    relationship: str
    entity: str
    time_delta_seconds: float = Field(ge=0)


class CorrelatedIncident(BaseModel):
    id: str
    event_ids: list[str]
    started_at: datetime
    ended_at: datetime
    links: list[CorrelationLink]


class AttackGraphNode(BaseModel):
    id: str
    entity_type: str
    key: str
    label: str
    risk_score: float = Field(default=0.0, ge=0, le=100)


class AttackGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship: str
    event_id: str
    timestamp: datetime


class AttackGraph(BaseModel):
    nodes: list[AttackGraphNode]
    edges: list[AttackGraphEdge]


class AttackGraphBuildRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[NormalizedEventCreate] = Field(min_length=1, max_length=MAX_EVENT_BATCH)


class EvidencePath(BaseModel):
    node_id: str
    summary: str
    supporting_edge_ids: list[str]
    supporting_event_ids: list[str]
    limitations: str


class RiskInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    threat_confidence: float = Field(ge=0, le=1)
    asset_criticality: float = Field(ge=0, le=1)
    attack_stage: float = Field(ge=0, le=1)
    anomaly_level: float = Field(ge=0, le=1)
    observed_at: datetime
    as_of: datetime

    @field_validator("observed_at", "as_of")
    @classmethod
    def timestamp_must_include_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("risk timestamps must include a timezone")
        return value


class RiskResult(BaseModel):
    score: float = Field(ge=0, le=100)
    level: Literal["low", "medium", "high", "critical"]
    components: dict[str, float]
    formula_version: str


class ResponseContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    event_type: str
    host: str | None = None
    user: str | None = None
    source_ip: IPv4Address | IPv6Address | None = None
    malicious_ip_confirmed: bool = False
    vulnerability_id: str | None = None


class ResponseRecommendation(BaseModel):
    action: Literal[
        "block_ip",
        "isolate_host",
        "reset_credentials",
        "investigate_endpoint",
        "patch_vulnerability",
        "monitor",
    ]
    target: str
    priority: Literal["low", "medium", "high", "critical"]
    rationale: str
    requires_human_approval: Literal[True] = True
    automatic_execution: Literal[False] = False
