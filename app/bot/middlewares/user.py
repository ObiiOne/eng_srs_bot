from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.config import settings
from app.db.session import SessionLocal
from app.repositories import users as users_repo


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = None
        if isinstance(event, (Message, CallbackQuery)):
            tg_user = event.from_user

        if tg_user is None:
            return await handler(event, data)

        if settings.allowed_ids and tg_user.id not in settings.allowed_ids:
            if isinstance(event, Message):
                await event.answer("⛔ Доступ запрещён.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Доступ запрещён.", show_alert=True)
            return

        async with SessionLocal() as db:
            user = await users_repo.get_or_create(db, tg_user.id, settings.default_timezone)
            await db.commit()
            data["db"] = db
            data["user"] = user
            return await handler(event, data)
