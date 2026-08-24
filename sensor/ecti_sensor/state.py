import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


@dataclass
class SensorState:
    last_successful_observation: str = field(
        default_factory=lambda: (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    )
    active_suspicious_processes: list[str] = field(default_factory=list)
    active_listeners: list[str] = field(default_factory=list)
    listeners_initialized: bool = False

    @classmethod
    def load(cls, path: Path) -> "SensorState":
        if not path.exists():
            return cls()
        try:
            raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            datetime.fromisoformat(str(raw["last_successful_observation"]))
            return cls(
                last_successful_observation=str(raw["last_successful_observation"]),
                active_suspicious_processes=list(raw.get("active_suspicious_processes", [])),
                active_listeners=list(raw.get("active_listeners", [])),
                listeners_initialized=bool(raw.get("listeners_initialized", False)),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return cls()

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(
                {
                    "last_successful_observation": self.last_successful_observation,
                    "active_suspicious_processes": self.active_suspicious_processes,
                    "active_listeners": self.active_listeners,
                    "listeners_initialized": self.listeners_initialized,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        temporary.replace(path)
