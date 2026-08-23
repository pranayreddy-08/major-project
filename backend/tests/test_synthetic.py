import ipaddress
import json
from pathlib import Path

from app.ingestion.synthetic import SyntheticConfig, generate_events, write_dataset


def test_synthetic_generator_is_deterministic_and_uses_documentation_networks() -> None:
    config = SyntheticConfig(count=20, seed=7)

    first = generate_events(config)
    second = generate_events(config)

    assert first == second
    assert {event["label"] for event in first} == {"attack", "benign"}
    for event in first:
        source = ipaddress.ip_address(str(event["source_ip"]))
        destination = ipaddress.ip_address(str(event["destination_ip"]))
        assert source in ipaddress.ip_network("192.0.2.0/24")
        assert destination in ipaddress.ip_network("198.51.100.0/24")


def test_dataset_manifest_records_version_checksum_and_no_real_data(tmp_path: Path) -> None:
    output = tmp_path / "sample.csv"
    manifest = tmp_path / "manifest.json"

    write_dataset(output, manifest, SyntheticConfig(count=5, seed=3))

    metadata = json.loads(manifest.read_text(encoding="utf-8"))
    assert metadata["dataset_id"] == "synthetic-events-v1"
    assert metadata["rows"] == 5
    assert metadata["contains_real_data"] is False
    assert len(metadata["sha256"]) == 64
