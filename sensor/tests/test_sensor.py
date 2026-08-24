import json
from datetime import datetime, timezone

import pytest

from ecti_sensor.collectors import map_windows_event, suspicious_process_reason
from ecti_sensor.config import SensorConfig
from ecti_sensor.state import SensorState


def test_defender_detection_maps_to_critical_malware_event() -> None:
    mapped = map_windows_event(
        {
            "Id": 1116,
            "RecordId": 42,
            "ProviderName": "Microsoft-Windows-Windows Defender",
            "TimeCreated": "2026-08-24T10:00:00+00:00",
            "Data": {"Threat Name": "Test-Sample"},
        },
        "workstation-01",
    )
    assert mapped is not None
    assert mapped["event"]["event_type"] == "malware_detected"
    assert mapped["event"]["severity"] == "critical"
    assert mapped["event"]["attributes"]["threat_name"] == "Test-Sample"


def test_failed_login_maps_source_and_user_without_raw_message() -> None:
    mapped = map_windows_event(
        {
            "Id": 4625,
            "RecordId": 84,
            "ProviderName": "Microsoft-Windows-Security-Auditing",
            "TimeCreated": "2026-08-24T10:01:00+00:00",
            "Data": {"IpAddress": "192.0.2.10", "TargetUserName": "local-user"},
        },
        "workstation-01",
    )
    assert mapped is not None
    assert mapped["event"]["event_type"] == "authentication_failure"
    assert mapped["event"]["source_ip"] == "192.0.2.10"
    assert mapped["event"]["user"] == "local-user"
    assert "message" not in mapped["event"]["attributes"]


@pytest.mark.parametrize(
    ("name", "path", "command", "expected"),
    [
        (
            "powershell.exe",
            "C:/Windows/powershell.exe",
            "powershell -EncodedCommand AAA",
            "encoded PowerShell command",
        ),
        (
            "mshta.exe",
            "C:/Windows/mshta.exe",
            "mshta https://example.invalid/a.hta",
            "remote HTA execution",
        ),
        ("notepad.exe", "C:/Windows/notepad.exe", "notepad notes.txt", None),
    ],
)
def test_suspicious_process_rules_are_narrow(
    name: str, path: str, command: str, expected: str | None
) -> None:
    assert suspicious_process_reason(name, path, command) == expected


def test_config_accepts_only_loopback_http_or_https(tmp_path) -> None:
    path = tmp_path / "sensor.json"
    path.write_text(
        json.dumps(
            {
                "api_url": "http://127.0.0.1:8000",
                "token": "a" * 64,
                "sensor_id": "windows-test-01",
                "interval_seconds": 60,
            }
        ),
        encoding="utf-8",
    )
    assert SensorConfig.load(path).api_url == "http://127.0.0.1:8000"
    path.write_text(path.read_text().replace("127.0.0.1", "192.0.2.10"), encoding="utf-8")
    with pytest.raises(ValueError, match="loopback"):
        SensorConfig.load(path)


def test_state_round_trip_is_atomic_and_timezone_aware(tmp_path) -> None:
    path = tmp_path / "state.json"
    state = SensorState(
        last_successful_observation=datetime.now(timezone.utc).isoformat(),
        active_suspicious_processes=["process-a"],
        active_listeners=["127.0.0.1:4444:1"],
        listeners_initialized=True,
    )
    state.save(path)
    assert SensorState.load(path) == state
