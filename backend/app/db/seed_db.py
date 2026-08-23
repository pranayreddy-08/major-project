import asyncio

from app.core.config import get_settings
from app.db.seed import seed_development_data
from app.db.session import AsyncSessionFactory


async def seed_non_production() -> None:
    environment = get_settings().app_environment.lower()
    if environment not in {"development", "staging"}:
        raise RuntimeError("synthetic demo seeding is allowed only in development or staging")
    async with AsyncSessionFactory() as session:
        await seed_development_data(session)


if __name__ == "__main__":
    asyncio.run(seed_non_production())
