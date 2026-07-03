"""
Базовый класс репозитория.

Все репозитории наследуются от BaseRepository и получают соединение
с PostgreSQL (asyncpg.Connection), пробрасываемое через DbSessionMiddleware.
"""

import asyncpg


# Тип соединения с БД — asyncpg.Connection
DbConnection = asyncpg.Connection


class BaseRepository:
    """
    Базовый репозиторий: хранит соединение с БД и передаёт его подклассам.

    Не содержит бизнес-логики — только инфраструктурный контракт.
    """

    def __init__(self, db: DbConnection) -> None:
        self.db = db
