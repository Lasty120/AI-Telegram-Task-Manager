from typing import Any, Awaitable, Callable, Dict

import asyncpg
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from database.repositories import UserRepository
from utils.context import user_lang


# Middleware для получения или создания пользователя при каждом Update.
# Использует UserRepository (asyncpg) вместо старых CRUD-функций aiosqlite.

class UserMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ):
        db: asyncpg.Connection = data["db"]
        tg_user = data["event_from_user"]

        # Если в Update нет отправителя — пропускаем без создания пользователя
        if not tg_user:
            return await handler(event, data)

        user_repo = UserRepository(db)

        # Пытаемся найти пользователя — если нет, создаём
        user = await user_repo.get_by_tg_id(tg_user.id)
        if not user:
            user = await user_repo.create(tg_id=tg_user.id, lang="ru")
            # Если create вернул None (гонка ON CONFLICT) — делаем повторный SELECT
            if not user:
                user = await user_repo.get_by_tg_id(tg_user.id)

        data["user"] = user

        # Устанавливаем язык пользователя в контекстную переменную
        lang = user["lang"] if user and "lang" in user else "ru"
        token = user_lang.set(lang)
        try:
            return await handler(event, data)
        finally:
            user_lang.reset(token)
