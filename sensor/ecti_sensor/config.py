import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def default_config_path() -> Path:
    program_data = os.getenv("PROGRAMDATA")
    if program_data:
        return Path(program_data) / "ECTI" / "sensor.json"
    return Path.home() / ".ecti" / "sensor.json"


@dataclass(frozen=True)
class SensorConfig:
    api_url: str
    token: str
    sensor_id: str
    interval_seconds: int
    state_path: Path
    log_path: Path

    @classmethod
    def load(cls, path: Path) -> "SensorConfig":
        raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        api_url = str(raw.get("api_url", "")).rstrip("/")
        token = str(raw.get("token", ""))
        sensor_id = str(raw.get("sensor_id", ""))
        interval = int(raw.get("interval_seconds", 60))
        if not api_url.startswith(("http://127.0.0.1:", "http://localhost:", "https://")):
            raise ValueError("api_url must use HTTPS or a loopback HTTP address")
        if len(token) < 32:
            raise ValueError("sensor token must contain at least 32 characters")
        if len(sensor_id) < 8:
            raise ValueError("sensor_id must contain at least 8 characters")
        if not 15 <= interval <= 3600:
            raise ValueError("interval_seconds must be between 15 and 3600")
        base = path.parent
        return cls(
            api_url=api_url,
            token=token,
            sensor_id=sensor_id,
            interval_seconds=interval,
            state_path=base / str(raw.get("state_file", "sensor-state.json")),
            log_path=base / str(raw.get("log_file", "sensor.log")),
        )
