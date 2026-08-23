import asyncio

import app.models  # noqa: F401
from app.core.config import get_settings
from app.db.base import Base
from app.db.seed import seed_development_data
from app.db.session import AsyncSessionFactory, engine


async def create_tables() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    if get_settings().app_environment.lower() != "production":
        async with AsyncSessionFactory() as session:
            await seed_development_data(session)


if __name__ == "__main__":
    asyncio.run(create_tables())
