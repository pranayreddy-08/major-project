import json
import platform
import socket
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from ecti_sensor import __version__
from ecti_sensor.collectors import CollectionResult, local_ip_addresses
from ecti_sensor.config import SensorConfig


def send_batch(
    config: SensorConfig,
    collection: CollectionResult,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    payload = {
        "sensor_id": config.sensor_id,
        "hostname": socket.gethostname(),
        "operating_system": platform.platform(),
        "agent_version": __version__,
        "observed_at": (observed_at or datetime.now(timezone.utc)).isoformat(),
        "ip_addresses": local_ip_addresses(),
        "capabilities": collection.capabilities,
        "events": collection.events,
    }
    request = urllib.request.Request(
        f"{config.api_url}/api/v1/sensors/ingest",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Sensor-Token": config.token,
            "User-Agent": f"ECTI-Sensor/{__version__}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read(512).decode("utf-8", errors="replace")
        raise RuntimeError(f"sensor API returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"sensor API is unavailable: {exc.reason}") from exc
