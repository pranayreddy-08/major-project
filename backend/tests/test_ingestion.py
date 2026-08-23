import json
from datetime import timezone
from pathlib import Path

from app.ingestion.adapters import ingest_csv, ingest_json, ingest_syslog
from app.ingestion.cli import export_result


def test_csv_ingestion_normalizes_aliases_preserves_raw_and_removes_duplicates(
    tmp_path: Path,
) -> None:
    source = tmp_path / "events.csv"
    source.write_text(
        "event_time,src_ip,dst_ip,username,hostname,proto,outcome,level,type,label\n"
        "2026-01-01 10:00:00,192.0.2.10,198.51.100.5,alice,HOST-01,TCP,"
        "Allowed,warning,login,attack\n"
        "2026-01-01 10:00:00,192.0.2.10,198.51.100.5,alice,HOST-01,TCP,"
        "Allowed,warning,login,attack\n",
        encoding="utf-8",
    )

    result = ingest_csv(source, log_source="demo-csv")

    assert len(result.accepted) == 1
    assert result.duplicates == 1
    assert not result.errors
    item = result.accepted[0]
    assert item.raw.payload["src_ip"] == "192.0.2.10"
    assert item.raw.source_reference == "events.csv:2"
    assert item.normalized.timestamp.tzinfo is timezone.utc
    assert item.normalized.protocol == "tcp"
    assert item.normalized.action == "allowed"
    assert item.normalized.attributes["label"] == "attack"


def test_json_ingestion_reports_bad_record_and_handles_missing_values(tmp_path: Path) -> None:
    source = tmp_path / "events.json"
    source.write_text(
        json.dumps(
            [
                {
                    "timestamp": "2026-01-01T11:00:00Z",
                    "source_ip": "N/A",
                    "severity": None,
                    "event_type": "heartbeat",
                },
                {
                    "timestamp": "not-a-time",
                    "source_ip": "192.0.2.1",
                    "event_type": "invalid",
                },
            ]
        ),
        encoding="utf-8",
    )

    result = ingest_json(source, log_source="demo-json")

    assert len(result.accepted) == 1
    assert len(result.errors) == 1
    assert result.accepted[0].normalized.source_ip is None
    assert result.accepted[0].normalized.severity.value == "informational"
    assert "unsupported timestamp" in result.errors[0].message


def test_syslog_ingestion_supports_rfc5424_and_rfc3164(tmp_path: Path) -> None:
    source = tmp_path / "events.log"
    source.write_text(
        "<34>1 2026-01-02T03:04:05Z edge-01 sshd 123 AUTH - "
        "source_ip=192.0.2.50 action=denied user=demo\n"
        "<13>Jan  2 03:05:00 edge-02 firewall[45]: "
        "source_ip=192.0.2.51 destination_ip=198.51.100.20 action=blocked\n"
        "this is not syslog\n",
        encoding="utf-8",
    )

    result = ingest_syslog(source, year=2026)

    assert len(result.accepted) == 2
    assert len(result.errors) == 1
    assert result.accepted[0].normalized.event_type == "AUTH"
    assert result.accepted[0].normalized.severity.value == "high"
    assert result.accepted[0].raw.payload["raw_message"].startswith("<34>1")
    assert str(result.accepted[1].normalized.destination_ip) == "198.51.100.20"
    assert result.errors[0].source_reference == "events.log:3"


def test_export_keeps_raw_and_normalized_streams_separate(tmp_path: Path) -> None:
    source = tmp_path / "events.jsonl"
    source.write_text(
        '{"timestamp":"2026-01-01T00:00:00Z","event_type":"demo","extra":7}\n',
        encoding="utf-8",
    )
    result = ingest_json(source, log_source="demo")
    raw_output = tmp_path / "raw.jsonl"
    normalized_output = tmp_path / "normalized.jsonl"

    export_result(result, raw_output, normalized_output)

    raw = json.loads(raw_output.read_text(encoding="utf-8"))
    normalized = json.loads(normalized_output.read_text(encoding="utf-8"))
    assert raw["payload"]["extra"] == 7
    assert normalized["attributes"]["extra"] == 7
    assert "checksum" in raw
    assert "checksum" not in normalized
