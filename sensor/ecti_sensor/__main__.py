import argparse
from pathlib import Path

from ecti_sensor.config import SensorConfig, default_config_path
from ecti_sensor.service import configure_logging, run_forever, run_once


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description="Collect defensive Windows telemetry for the local ECTI platform."
    )
    command.add_argument(
        "--config",
        type=Path,
        default=default_config_path(),
        help="Path to sensor.json (default: ProgramData/ECTI/sensor.json)",
    )
    command.add_argument(
        "--once", action="store_true", help="Collect and send one batch, then exit."
    )
    return command


def main() -> None:
    args = parser().parse_args()
    config = SensorConfig.load(args.config)
    configure_logging(config)
    if args.once:
        run_once(config)
    else:
        run_forever(config)


if __name__ == "__main__":
    main()
