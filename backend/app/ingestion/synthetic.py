import argparse
import csv
import hashlib
import json
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


@dataclass(frozen=True)
class SyntheticConfig:
    count: int = 120
    seed: int = 42
    start: datetime = datetime(2026, 1, 1, tzinfo=timezone.utc)
    interval_seconds: int = 60
    dataset_version: str = "synthetic-events-v1"


FIELDNAMES = (
    "timestamp",
    "source_ip",
    "destination_ip",
    "user",
    "host",
    "protocol",
    "action",
    "severity",
    "log_source",
    "event_type",
    "destination_port",
    "bytes_transferred",
    "failed_attempts",
    "label",
)


def generate_events(config: SyntheticConfig) -> list[dict[str, object]]:
    if config.count < 1:
        raise ValueError("count must be positive")
    generator = random.Random(config.seed)
    events: list[dict[str, object]] = []

    for index in range(config.count):
        timestamp = config.start + timedelta(seconds=index * config.interval_seconds)
        source_host = (index % 40) + 1
        destination_host = ((index * 7) % 40) + 1
        attack_kind = index % 10
        is_attack = attack_kind in {0, 7}

        if is_attack and attack_kind == 0:
            event_type = "authentication_failure"
            severity = "high"
            action = "denied"
            failed_attempts = generator.randint(5, 12)
            destination_port = 22
        elif is_attack:
            event_type = "port_scan"
            severity = "critical"
            action = "blocked"
            failed_attempts = 0
            destination_port = generator.choice((22, 80, 443, 3389))
        else:
            event_type = generator.choice(("network_connection", "authentication_success"))
            severity = generator.choice(("informational", "low"))
            action = "allowed"
            failed_attempts = 0
            destination_port = generator.choice((53, 80, 123, 443))

        events.append(
            {
                "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
                "source_ip": f"192.0.2.{source_host}",
                "destination_ip": f"198.51.100.{destination_host}",
                "user": f"demo-user-{(index % 12) + 1:02d}",
                "host": f"demo-host-{source_host:02d}",
                "protocol": "tcp" if destination_port != 53 else "udp",
                "action": action,
                "severity": severity,
                "log_source": "synthetic",
                "event_type": event_type,
                "destination_port": destination_port,
                "bytes_transferred": generator.randint(128, 50_000),
                "failed_attempts": failed_attempts,
                "label": "attack" if is_attack else "benign",
            }
        )
    return events


def write_dataset(output: Path, manifest: Path, config: SyntheticConfig) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(generate_events(config))

    checksum = hashlib.sha256(output.read_bytes()).hexdigest()
    serialized_config = asdict(config)
    serialized_config["start"] = config.start.isoformat()
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "dataset_id": config.dataset_version,
                "schema_version": "normalized-event-v1",
                "generator": "app.ingestion.synthetic",
                "generator_config": serialized_config,
                "file": output.name,
                "sha256": checksum,
                "rows": config.count,
                "contains_real_data": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic anonymized security logs")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--count", type=int, default=120)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    write_dataset(
        args.output,
        args.manifest,
        SyntheticConfig(count=args.count, seed=args.seed),
    )


if __name__ == "__main__":
    main()
