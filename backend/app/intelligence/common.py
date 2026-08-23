import hashlib
import json

from app.schemas.events import NormalizedEventCreate


def stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{digest}"


def event_id(event: NormalizedEventCreate) -> str:
    payload = event.model_dump(mode="json", exclude={"raw_event_id"})
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return stable_id("evt", canonical)


def event_entities(event: NormalizedEventCreate) -> tuple[tuple[str, str], ...]:
    entities: list[tuple[str, str]] = []
    for address in (event.source_ip, event.destination_ip):
        if address is not None:
            entities.append(("ip", str(address)))
    if event.user:
        entities.append(("user", event.user.strip().lower()))
    if event.host:
        entities.append(("host", event.host.strip().lower()))
    return tuple(sorted(set(entities)))
