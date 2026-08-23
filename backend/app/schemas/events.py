from datetime import datetime
from enum import Enum
from ipaddress import IPv4Address, IPv6Address
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventSeverity(str, Enum):
    informational = "informational"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class NormalizedEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    source_ip: IPv4Address | IPv6Address | None = None
    destination_ip: IPv4Address | IPv6Address | None = None
    user: str | None = Field(default=None, max_length=255)
    host: str | None = Field(default=None, max_length=255)
    protocol: str | None = Field(default=None, max_length=50)
    action: str | None = Field(default=None, max_length=100)
    severity: EventSeverity
    log_source: str = Field(min_length=1, max_length=100)
    event_type: str = Field(min_length=1, max_length=100)
    raw_event_id: UUID | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_include_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value


class NormalizedEventRead(NormalizedEventCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
