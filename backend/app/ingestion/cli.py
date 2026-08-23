import argparse
import json
from collections.abc import Callable
from pathlib import Path

from app.ingestion.adapters import ingest_csv, ingest_json, ingest_syslog
from app.ingestion.models import IngestionResult


def _write_jsonl(path: Path, values: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as output_file:
        for value in values:
            output_file.write(json.dumps(value, sort_keys=True))
            output_file.write("\n")


def export_result(result: IngestionResult, raw_output: Path, normalized_output: Path) -> None:
    _write_jsonl(raw_output, [item.raw.model_dump(mode="json") for item in result.accepted])
    _write_jsonl(
        normalized_output,
        [item.normalized.model_dump(mode="json") for item in result.accepted],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize raw security events into JSONL files")
    parser.add_argument("input", type=Path)
    parser.add_argument("--format", choices=("csv", "json", "syslog"), required=True)
    parser.add_argument("--log-source", required=True)
    parser.add_argument("--raw-output", type=Path, required=True)
    parser.add_argument("--normalized-output", type=Path, required=True)
    args = parser.parse_args()

    adapters: dict[str, Callable[..., IngestionResult]] = {
        "csv": ingest_csv,
        "json": ingest_json,
        "syslog": ingest_syslog,
    }
    result = adapters[args.format](args.input, log_source=args.log_source)
    export_result(result, args.raw_output, args.normalized_output)
    print(
        json.dumps(
            {
                "accepted": len(result.accepted),
                "duplicates": result.duplicates,
                "errors": [error.model_dump() for error in result.errors],
            },
            indent=2,
        )
    )
    return 0 if not result.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
