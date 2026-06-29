from typing import Any, Awaitable, Callable, Dict

import asyncpg
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from database.crud.user import get_or_create_user
from utils.context import user_lang


# Middleware на получение и создание юзера.

class UserMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ):

        db: asyncpg.Connection = data["db"]
        tg_user = data["event_from_user"]
        if not tg_user:
            return await handler(event, data)

        # Передаём соединение db в CRUD-функцию (её сигнатура и реализация
        # под asyncpg.Connection переводятся отдельно, вне рамок этой middleware)
        user = await get_or_create_user(
            db=db,
            tg_id=tg_user.id,
        )

        data["user"] = user

        lang = user["lang"] if "lang" in user.keys() else "ru"
        token = user_lang.set(lang)
        try:
            return await handler(event, data)
        finally:
            user_lang.reset(token)
