from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

import aiosqlite

# Импортируй свою обновленную функцию CRUD
from database.crud.user import get_or_create_user


# Middleware на получение и создание юзера
class UserMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ):

        db: aiosqlite.Connection = data["db"]
        tg_user = data["event_from_user"]

        # Передаем соединение db в твою CRUD функцию
        user = await get_or_create_user(
            db=db,
            tg_id=tg_user.id,
        )

        data["user"] = user

        return await handler(event, data)