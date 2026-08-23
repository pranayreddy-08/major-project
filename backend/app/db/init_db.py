import asyncio

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import engine


async def create_tables() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(create_tables())
