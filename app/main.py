import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import early, pairs, session, start, stats, verbs
from app.bot.middlewares.user import UserMiddleware
from app.config import settings
from app.db.base import Base
from app.db.migrations import ensure_columns
from app.db.session import engine
from app.domain.verbs import VerbConfigError, load_verbs


def setup_logging() -> None:
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await ensure_columns(conn)


async def main() -> None:
    setup_logging()

    try:
        load_verbs(settings.verbs_path)
    except VerbConfigError as e:
        logging.error("Ошибка в файле глаголов: %s", e)
        sys.exit(1)

    await init_db()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())

    # порядок важен: /start обрабатывается раньше текстовых ответов сессии
    dp.include_router(start.router)
    dp.include_router(pairs.router)
    dp.include_router(session.router)
    dp.include_router(early.router)
    dp.include_router(stats.router)
    dp.include_router(verbs.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
    
    