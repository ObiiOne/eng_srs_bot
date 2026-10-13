from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


async def get_by_telegram_id(db: AsyncSession, telegram_id: int) -> User | None:
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_or_create(db: AsyncSession, telegram_id: int, default_timezone: str) -> User:
    user = await get_by_telegram_id(db, telegram_id)
    if user is None:
        user = User(telegram_id=telegram_id, timezone=default_timezone)
        db.add(user)
        await db.flush()
    return user
