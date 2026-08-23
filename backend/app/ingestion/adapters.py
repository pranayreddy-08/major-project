import csv
import json
import re
import shlex
from collections.abc import Iterator, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.ingestion.models import IngestionError, IngestionResult
from app.ingestion.normalizer import ingest_records

RFC5424_PATTERN = re.compile(
    r"^<(?P<priority>\d{1,3})>(?P<version>\d+)\s+"
    r"(?P<timestamp>\S+)\s+(?P<host>\S+)\s+(?P<app>\S+)\s+"
    r"(?P<process>\S+)\s+(?P<message_id>\S+)\s+"
    r"(?P<structured>-|(?:\[[^\]]*\])+)(?:\s+(?P<message>.*))?$"
)
RFC3164_PATTERN = re.compile(
    r"^<(?P<priority>\d{1,3})>(?P<timestamp>[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>\S+)\s+(?P<app>[^:\[]+)(?:\[(?P<process>\d+)\])?:\s*(?P<message>.*)$"
)


def ingest_csv(
    path: str | Path,
    *,
    log_source: str,
    field_mapping: Mapping[str, str] | None = None,
    existing_checksums: set[str] | None = None,
) -> IngestionResult:
    source_path = Path(path)

    def records() -> Iterator[tuple[str, Mapping[str, Any]]]:
        with source_path.open("r", encoding="utf-8-sig", newline="") as source_file:
            reader = csv.DictReader(source_file)
            if not reader.fieldnames:
                raise ValueError("CSV input must contain a header row")
            for row_number, row in enumerate(reader, start=2):
                yield f"{source_path.name}:{row_number}", dict(row)

    return ingest_records(
        records(),
        log_source=log_source,
        field_mapping=field_mapping,
        existing_checksums=existing_checksums,
    )


def _json_records(source_path: Path) -> Iterator[tuple[str, Mapping[str, Any]]]:
    if source_path.suffix.lower() in {".jsonl", ".ndjson"}:
        with source_path.open("r", encoding="utf-8-sig") as source_file:
            for line_number, line in enumerate(source_file, start=1):
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"{source_path.name}:{line_number} must be a JSON object")
                yield f"{source_path.name}:{line_number}", value
        return

    with source_path.open("r", encoding="utf-8-sig") as source_file:
        value = json.load(source_file)
    if isinstance(value, dict) and isinstance(value.get("events"), list):
        value = value["events"]
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        raise ValueError("JSON input must be an object, array of objects, or an events array")
    for item_number, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"{source_path.name}:{item_number} must be a JSON object")
        yield f"{source_path.name}:{item_number}", item


def ingest_json(
    path: str | Path,
    *,
    log_source: str,
    field_mapping: Mapping[str, str] | None = None,
    existing_checksums: set[str] | None = None,
) -> IngestionResult:
    source_path = Path(path)
    return ingest_records(
        _json_records(source_path),
        log_source=log_source,
        field_mapping=field_mapping,
        existing_checksums=existing_checksums,
    )


def _message_fields(message: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    remainder: list[str] = []
    try:
        tokens = shlex.split(message)
    except ValueError:
        tokens = message.split()
    for token in tokens:
        if "=" not in token:
            remainder.append(token)
            continue
        key, value = token.split("=", 1)
        if key:
            fields[key] = value
        else:
            remainder.append(token)
    if remainder:
        fields["message"] = " ".join(remainder)
    return fields


def _parse_syslog_line(line: str, *, year: int) -> dict[str, Any]:
    match = RFC5424_PATTERN.match(line)
    if match:
        values = match.groupdict()
        message = values.get("message") or ""
        payload: dict[str, Any] = {
            "raw_message": line,
            "timestamp": values["timestamp"],
            "host": values["host"],
            "event_type": (values["message_id"] if values["message_id"] != "-" else values["app"]),
            "severity": int(values["priority"]) % 8,
            "application": values["app"],
            "process_id": None if values["process"] == "-" else values["process"],
            "structured_data": values["structured"],
        }
        payload.update(_message_fields(message))
        return payload

    match = RFC3164_PATTERN.match(line)
    if match:
        values = match.groupdict()
        timestamp = datetime.strptime(values["timestamp"], "%b %d %H:%M:%S").replace(
            year=year, tzinfo=timezone.utc
        )
        payload = {
            "raw_message": line,
            "timestamp": timestamp.isoformat(),
            "host": values["host"],
            "event_type": values["app"].strip(),
            "severity": int(values["priority"]) % 8,
            "application": values["app"].strip(),
            "process_id": values.get("process"),
        }
        payload.update(_message_fields(values.get("message") or ""))
        return payload

    raise ValueError("record is not valid RFC 5424 or RFC 3164 syslog")


def ingest_syslog(
    path: str | Path,
    *,
    log_source: str = "syslog",
    existing_checksums: set[str] | None = None,
    year: int | None = None,
) -> IngestionResult:
    source_path = Path(path)
    parsed_records: list[tuple[str, Mapping[str, Any]]] = []
    parse_errors: list[IngestionError] = []
    assumed_year = year or datetime.now(timezone.utc).year

    with source_path.open("r", encoding="utf-8-sig") as source_file:
        for line_number, line in enumerate(source_file, start=1):
            if not line.strip():
                continue
            reference = f"{source_path.name}:{line_number}"
            try:
                payload = _parse_syslog_line(line.rstrip("\r\n"), year=assumed_year)
            except ValueError as error:
                parse_errors.append(IngestionError(source_reference=reference, message=str(error)))
                continue
            parsed_records.append((reference, payload))

    result = ingest_records(
        parsed_records,
        log_source=log_source,
        existing_checksums=existing_checksums,
    )
    result.errors = [*parse_errors, *result.errors]
    return result
