from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.v1 import sensors
from app.schemas.platform import InitialAdministratorCreate
from app.schemas.sensors import SensorIngestRequest


def settings(token: str | None) -> SimpleNamespace:
    return SimpleNamespace(sensor_ingest_token=token, sensor_offline_seconds=180)


def test_sensor_token_uses_fail_closed_authentication(monkeypatch) -> None:
    monkeypatch.setattr(sensors, "get_settings", lambda: settings("a" * 64))
    sensors.require_sensor_token("a" * 64)
    with pytest.raises(HTTPException) as rejected:
        sensors.require_sensor_token("b" * 64)
    assert rejected.value.status_code == 401


def test_unconfigured_sensor_ingestion_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(sensors, "get_settings", lambda: settings(None))
    with pytest.raises(HTTPException) as unavailable:
        sensors.require_sensor_token(None)
    assert unavailable.value.status_code == 503


def test_sensor_online_window(monkeypatch) -> None:
    monkeypatch.setattr(sensors, "get_settings", lambda: settings("a" * 64))
    now = datetime.now(timezone.utc)
    assert sensors.sensor_is_online(now - timedelta(seconds=179), now)
    assert not sensors.sensor_is_online(now - timedelta(seconds=181), now)


def test_owner_and_sensor_contracts_reject_weak_or_unbounded_input() -> None:
    with pytest.raises(ValidationError):
        InitialAdministratorCreate(username="owner", full_name="Owner", password="short")
    with pytest.raises(ValidationError):
        SensorIngestRequest(
            sensor_id="short",
            hostname="host",
            operating_system="Windows",
            agent_version="1",
            observed_at=datetime.now(timezone.utc),
        )
