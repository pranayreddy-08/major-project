import hashlib
import json
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone, tzinfo
from typing import Any

from pydantic import ValidationError

from app.ingestion.models import (
    IngestedEvent,
    IngestionError,
    IngestionResult,
    RawEventEnvelope,
)
from app.schemas.events import EventSeverity, NormalizedEventCreate

FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "timestamp": ("timestamp", "time", "event_time", "datetime", "date"),
    "source_ip": ("source_ip", "src_ip", "srcip", "source", "client_ip"),
    "destination_ip": ("destination_ip", "dest_ip", "dst_ip", "dstip", "destination"),
    "user": ("user", "username", "account", "principal"),
    "host": ("host", "hostname", "device", "asset"),
    "protocol": ("protocol", "proto", "transport"),
    "action": ("action", "outcome", "decision", "verdict"),
    "severity": ("severity", "level", "priority"),
    "log_source": ("log_source", "source_type", "sensor"),
    "event_type": ("event_type", "type", "category", "event_name"),
}

MISSING_VALUES = {"", "-", "n/a", "na", "none", "null", "nan", "unknown"}


def checksum_payload(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_timestamp(value: Any, default_timezone: tzinfo = timezone.utc) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, int | float):
        seconds = value / 1000 if abs(value) >= 100_000_000_000 else value
        parsed = datetime.fromtimestamp(seconds, tz=timezone.utc)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("timestamp is required")
        try:
            number = float(text)
        except ValueError:
            normalized = f"{text[:-1]}+00:00" if text.endswith(("Z", "z")) else text
            try:
                parsed = datetime.fromisoformat(normalized)
            except ValueError as error:
                formats = (
                    "%Y-%m-%d %H:%M:%S",
                    "%Y/%m/%d %H:%M:%S",
                    "%d/%m/%Y %H:%M:%S",
                    "%m/%d/%Y %H:%M:%S",
                )
                for timestamp_format in formats:
                    try:
                        parsed = datetime.strptime(text, timestamp_format)
                        break
                    except ValueError:
                        continue
                else:
                    raise ValueError(f"unsupported timestamp: {text}") from error
        else:
            return parse_timestamp(number, default_timezone)
    else:
        raise ValueError("timestamp is required")

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=default_timezone)
    return parsed.astimezone(timezone.utc)


def parse_severity(value: Any) -> EventSeverity:
    if value is None:
        return EventSeverity.informational
    if isinstance(value, int | float) or (isinstance(value, str) and value.strip().isdigit()):
        code = int(value)
        if code <= 1:
            return EventSeverity.critical
        if code == 2:
            return EventSeverity.high
        if code == 3:
            return EventSeverity.medium
        if code == 4:
            return EventSeverity.low
        return EventSeverity.informational

    aliases = {
        "emergency": EventSeverity.critical,
        "alert": EventSeverity.critical,
        "fatal": EventSeverity.critical,
        "error": EventSeverity.high,
        "err": EventSeverity.high,
        "warning": EventSeverity.medium,
        "warn": EventSeverity.medium,
        "notice": EventSeverity.low,
        "info": EventSeverity.informational,
        "debug": EventSeverity.informational,
    }
    text = str(value).strip().lower()
    try:
        return EventSeverity(text)
    except ValueError:
        if text in aliases:
            return aliases[text]
        raise ValueError(f"unsupported severity: {value}") from None


def _clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return None if stripped.lower() in MISSING_VALUES else stripped
    return value


def normalize_record(
    payload: Mapping[str, Any],
    *,
    default_log_source: str,
    field_mapping: Mapping[str, str] | None = None,
    default_timezone: tzinfo = timezone.utc,
) -> NormalizedEventCreate:
    mapping = field_mapping or {}
    original_by_lower = {str(key).strip().lower(): key for key in payload}
    consumed: set[object] = set()
    common: dict[str, Any] = {}

    for canonical, aliases in FIELD_ALIASES.items():
        candidates = (mapping[canonical],) if canonical in mapping else aliases
        for candidate in candidates:
            original_key = original_by_lower.get(candidate.strip().lower())
            if original_key is not None:
                consumed.add(original_key)
                common[canonical] = _clean(payload[original_key])
                break

    attributes = {
        str(key): cleaned
        for key, value in payload.items()
        if key not in consumed and (cleaned := _clean(value)) is not None
    }
    protocol = common.get("protocol")
    action = common.get("action")

    return NormalizedEventCreate(
        timestamp=parse_timestamp(common.get("timestamp"), default_timezone),
        source_ip=common.get("source_ip"),
        destination_ip=common.get("destination_ip"),
        user=common.get("user"),
        host=common.get("host"),
        protocol=str(protocol).lower() if protocol is not None else None,
        action=str(action).lower() if action is not None else None,
        severity=parse_severity(common.get("severity")),
        log_source=str(common.get("log_source") or default_log_source),
        event_type=str(common.get("event_type") or "unknown"),
        attributes=attributes,
    )


def ingest_records(
    records: Iterable[tuple[str, Mapping[str, Any]]],
    *,
    log_source: str,
    field_mapping: Mapping[str, str] | None = None,
    existing_checksums: set[str] | None = None,
    default_timezone: tzinfo = timezone.utc,
) -> IngestionResult:
    result = IngestionResult()
    seen = set(existing_checksums or set())

    for source_reference, payload in records:
        raw_payload = dict(payload)
        checksum = checksum_payload(raw_payload)
        if checksum in seen:
            result.duplicates += 1
            continue
        seen.add(checksum)

        try:
            normalized = normalize_record(
                raw_payload,
                default_log_source=log_source,
                field_mapping=field_mapping,
                default_timezone=default_timezone,
            )
            raw = RawEventEnvelope(
                log_source=log_source,
                source_reference=source_reference,
                checksum=checksum,
                payload=raw_payload,
            )
        except (TypeError, ValueError, ValidationError) as error:
            result.errors.append(
                IngestionError(source_reference=source_reference, message=str(error))
            )
            continue

        result.accepted.append(IngestedEvent(raw=raw, normalized=normalized))

    return result
