import argparse
import json
from pathlib import Path

from ecti_ml.config import PreprocessingConfig
from ecti_ml.preprocessing import prepare_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a time-ordered dataset without leakage")
    parser.add_argument("input", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path)
    args = parser.parse_args()

    config = PreprocessingConfig.from_json(args.config)
    prepared = prepare_csv(str(args.input), config)
    summary = {
        "dataset_version": prepared.dataset_version,
        "config_version": prepared.config_version,
        "feature_count": len(prepared.feature_names),
        "feature_names": prepared.feature_names,
        "rows": {
            "train": len(prepared.train.labels),
            "validation": len(prepared.validation.labels),
            "test": len(prepared.test.labels),
        },
        "time_boundaries": {
            "train_end": prepared.train.timestamps.max().isoformat(),
            "validation_start": prepared.validation.timestamps.min().isoformat(),
            "validation_end": prepared.validation.timestamps.max().isoformat(),
            "test_start": prepared.test.timestamps.min().isoformat(),
        },
    }
    serialized = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    print(serialized, end="")
    if args.summary_output:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(serialized, encoding="utf-8")


if __name__ == "__main__":
    main()
