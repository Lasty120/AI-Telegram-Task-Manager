from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable
from aiogram.types import TelegramObject

import aiosqlite


# Middleware на создание изолированных соединений с БД
class DbSessionMiddleware(BaseMiddleware):
    def __init__(self, db_path: str):
        self.db_path = db_path
        super().__init__()

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        # Открываем соединение с базой данных на каждый запрос
        async with aiosqlite.connect(self.db_path) as db:
            # Чтобы была возможность работать со строками как со словарями (по именам колонок):
            db.row_factory = aiosqlite.Row

            data["db"] = db
            return await handler(event, data)