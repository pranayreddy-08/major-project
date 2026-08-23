import asyncio
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

import app.models  # noqa: F401
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine

ALEMBIC_TABLE = "alembic_version"
BASELINE_ENVIRONMENTS = {"development", "staging"}


def baseline_required(existing_tables: set[str], environment: str) -> bool:
    if ALEMBIC_TABLE in existing_tables:
        return False
    expected_tables = set(Base.metadata.tables)
    present_application_tables = existing_tables & expected_tables
    if not present_application_tables:
        return False
    missing_tables = expected_tables - present_application_tables
    if missing_tables:
        missing = ", ".join(sorted(missing_tables))
        raise RuntimeError(f"refusing to baseline a partial application schema; missing: {missing}")
    if environment.lower() not in BASELINE_ENVIRONMENTS:
        raise RuntimeError(
            "an existing unversioned production schema requires explicit operator review"
        )
    return True


async def existing_tables() -> set[str]:
    async with engine.connect() as connection:
        return set(await connection.run_sync(lambda sync: inspect(sync).get_table_names()))


def alembic_config() -> Config:
    config_path = Path(os.getenv("ALEMBIC_CONFIG", "alembic.ini")).resolve()
    return Config(str(config_path))


def migrate_to_head() -> None:
    settings = get_settings()
    tables = asyncio.run(existing_tables())
    configuration = alembic_config()
    if baseline_required(tables, settings.app_environment):
        command.stamp(configuration, "head")
    command.upgrade(configuration, "head")


if __name__ == "__main__":
    migrate_to_head()
