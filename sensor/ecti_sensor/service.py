import logging
import time
from datetime import datetime, timezone

from ecti_sensor.client import send_batch
from ecti_sensor.collectors import collect
from ecti_sensor.config import SensorConfig
from ecti_sensor.state import SensorState

LOGGER = logging.getLogger("ecti_sensor")


def configure_logging(config: SensorConfig) -> None:
    config.log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(config.log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def run_once(config: SensorConfig) -> dict:
    state = SensorState.load(config.state_path)
    observed_at = datetime.now(timezone.utc)
    collection = collect(state, observed_at)
    response = send_batch(config, collection, observed_at)
    collection.next_state.save(config.state_path)
    LOGGER.info(
        "heartbeat accepted=%s duplicates=%s alerts=%s",
        response.get("accepted_events", 0),
        response.get("duplicate_events", 0),
        response.get("stored_alerts", 0),
    )
    return response


def run_forever(config: SensorConfig) -> None:
    while True:
        try:
            run_once(config)
        except Exception:
            LOGGER.exception("sensor collection cycle failed")
        time.sleep(config.interval_seconds)
