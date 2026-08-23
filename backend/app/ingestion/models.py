from pydantic import BaseModel, ConfigDict, Field

from app.schemas.events import NormalizedEventCreate


class RawEventEnvelope(BaseModel):
    """Source record retained unchanged enough to replay normalization."""

    model_config = ConfigDict(extra="forbid")

    log_source: str = Field(min_length=1, max_length=100)
    source_reference: str = Field(min_length=1, max_length=500)
    checksum: str = Field(min_length=64, max_length=64)
    payload: dict[str, object]


class IngestedEvent(BaseModel):
    raw: RawEventEnvelope
    normalized: NormalizedEventCreate


class IngestionError(BaseModel):
    source_reference: str
    message: str


class IngestionResult(BaseModel):
    accepted: list[IngestedEvent] = Field(default_factory=list)
    errors: list[IngestionError] = Field(default_factory=list)
    duplicates: int = 0

    @property
    def processed(self) -> int:
        return len(self.accepted) + len(self.errors) + self.duplicates
