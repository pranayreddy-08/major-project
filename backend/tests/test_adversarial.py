import json
from datetime import timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.ingestion.adapters import ingest_json
from app.ingestion.normalizer import ingest_records, normalize_record
from app.schemas.events import MAX_EVENT_BATCH, NormalizedEventCreate
from app.schemas.platform import FeedbackCreate


def valid_event() -> dict[str, object]:
    return {
        "timestamp": "2026-01-01T00:00:00Z",
        "source_ip": "192.0.2.44",
        "destination_ip": "198.51.100.20",
        "severity": "high",
        "log_source": "adversarial-test",
        "event_type": "authentication_failure",
    }


@pytest.mark.parametrize(
    ("mutation", "expected_fragment"),
    [
        ({"timestamp": None}, "timestamp is required"),
        ({"timestamp": "not-a-time"}, "unsupported timestamp"),
        ({"source_ip": "999.999.999.999"}, "not a valid IPv"),
        ({"severity": "catastrophic"}, "unsupported severity"),
    ],
)
def test_bad_records_are_isolated_without_dropping_valid_neighbors(
    mutation: dict[str, object], expected_fragment: str
) -> None:
    bad = valid_event() | mutation
    result = ingest_records(
        [("good:1", valid_event()), ("bad:2", bad)],
        log_source="adversarial-test",
    )

    assert len(result.accepted) == 1
    assert len(result.errors) == 1
    assert expected_fragment in result.errors[0].message


def test_duplicate_and_unusual_timestamps_are_normalized_deterministically() -> None:
    epoch_ms = valid_event() | {"timestamp": 1767225600000}
    result = ingest_records(
        [("first", epoch_ms), ("duplicate", epoch_ms)],
        log_source="adversarial-test",
    )

    assert len(result.accepted) == 1
    assert result.duplicates == 1
    assert result.accepted[0].normalized.timestamp.tzinfo is timezone.utc
    naive = normalize_record(
        valid_event() | {"timestamp": "2026-01-01 05:30:00"},
        default_log_source="adversarial-test",
    )
    assert naive.timestamp.isoformat() == "2026-01-01T05:30:00+00:00"


def test_malformed_json_is_rejected_before_partial_processing(tmp_path: Path) -> None:
    source = tmp_path / "malformed.json"
    source.write_text('{"events": [', encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        ingest_json(source, log_source="adversarial-test")


def test_oversized_workflow_batch_is_rejected_at_api_boundary(authenticated_client) -> None:
    payload = {
        "events": [valid_event()] * (MAX_EVENT_BATCH + 1),
        "as_of": "2026-01-01T01:00:00Z",
    }

    response = authenticated_client.post("/api/v1/workflows/analyze", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "too_long"


def test_extra_fields_naive_times_and_oversized_feedback_are_rejected() -> None:
    with pytest.raises(ValidationError):
        NormalizedEventCreate.model_validate(valid_event() | {"unexpected": "payload"})
    with pytest.raises(ValidationError):
        NormalizedEventCreate.model_validate(valid_event() | {"timestamp": "2026-01-01 00:00:00"})
    with pytest.raises(ValidationError):
        FeedbackCreate(verdict="needs_review", comment="x" * 2001)
