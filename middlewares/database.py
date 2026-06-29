from typing import Any, Awaitable, Callable, Dict

import asyncpg
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


# Middleware на выдачу изолированного соединения с БД на каждый Update.
class DbSessionMiddleware(BaseMiddleware):
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        super().__init__()

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        # Берём соединение из пула на время обработки одного Update от Telegram
        async with self.pool.acquire() as connection:
            # Транзакция на весь Update: если хендлер выбросит исключение —
            # все изменения в БД за это соединение откатятся автоматически
            async with connection.transaction():
                data["db"] = connection
                return await handler(event, data)
