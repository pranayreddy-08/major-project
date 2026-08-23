import asyncio

from app.db.seed import seed_user_accounts
from app.db.session import AsyncSessionFactory


async def bootstrap_users() -> None:
    async with AsyncSessionFactory() as session:
        await seed_user_accounts(session)
        await session.commit()


if __name__ == "__main__":
    asyncio.run(bootstrap_users())
