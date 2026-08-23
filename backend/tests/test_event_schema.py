from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.events import EventSeverity, NormalizedEventCreate


def test_normalized_event_accepts_common_fields() -> None:
    event = NormalizedEventCreate(
        timestamp=datetime(2026, 1, 15, 8, 30, tzinfo=timezone.utc),
        source_ip="192.0.2.10",
        destination_ip="198.51.100.7",
        user="analyst",
        host="workstation-01",
        protocol="TCP",
        action="allowed",
        severity=EventSeverity.medium,
        log_source="firewall",
        event_type="network_connection",
    )

    assert str(event.source_ip) == "192.0.2.10"
    assert event.severity is EventSeverity.medium


def test_normalized_event_rejects_timestamp_without_timezone() -> None:
    with pytest.raises(ValidationError, match="timestamp must include a timezone"):
        NormalizedEventCreate(
            timestamp=datetime(2026, 1, 15, 8, 30),
            severity=EventSeverity.low,
            log_source="demo",
            event_type="authentication",
        )
