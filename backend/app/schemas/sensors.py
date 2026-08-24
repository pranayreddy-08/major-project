from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.events import NormalizedEventCreate

MAX_SENSOR_EVENT_BATCH = 500


class SensorEventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_key: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    event: NormalizedEventCreate


class SensorIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sensor_id: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9_.:-]+$")
    hostname: str = Field(min_length=1, max_length=255)
    operating_system: str = Field(min_length=1, max_length=255)
    agent_version: str = Field(min_length=1, max_length=50)
    observed_at: datetime
    ip_addresses: list[str] = Field(default_factory=list, max_length=32)
    capabilities: dict[str, Any] = Field(default_factory=dict)
    events: list[SensorEventEnvelope] = Field(
        default_factory=list, max_length=MAX_SENSOR_EVENT_BATCH
    )

    @field_validator("observed_at")
    @classmethod
    def observed_at_must_include_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a timezone")
        return value


class SensorIngestResponse(BaseModel):
    accepted_events: int = Field(ge=0)
    duplicate_events: int = Field(ge=0)
    stored_alerts: int = Field(ge=0)
    workflow_id: str | None = None


class EndpointSensorRead(BaseModel):
    id: UUID
    sensor_id: str
    hostname: str
    operating_system: str
    agent_version: str
    ip_addresses: list[str]
    capabilities: dict[str, Any]
    last_seen_at: datetime
    last_event_at: datetime | None
    status: Literal["online", "offline"]


class SensorServiceStatus(BaseModel):
    ingest_configured: bool
    sensors_total: int = Field(ge=0)
    sensors_online: int = Field(ge=0)
