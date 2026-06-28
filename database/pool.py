"""
Слой подключения к PostgresSQL через asyncpg.

Хранит единственный на всё приложение пул соединений (синглтон через
модульную переменную) и предоставляет функции для его создания,
получения и закрытия. Это замена старому `database/init_db.py`,
который работал с SQLite через aiosqlite.
"""

import logging

import asyncpg

from config import DB_URL, POOL_MAX_SIZE, POOL_MIN_SIZE

logger = logging.getLogger(__name__)



# Модульная переменная — единственный экземпляр пула на всё приложение
_pool: asyncpg.Pool | None = None




async def create_pool() -> asyncpg.Pool:
    """
    Создаёт пул соединений asyncpg и сохраняет его как глобальный синглтон.

    Должна вызываться один раз при старте приложения (в main.py),
    до запуска миграций и до начала обработки обновлений бота.
    """
    global _pool

    if _pool is not None:
        # Пул уже создан — повторно не пересоздаём, чтобы не плодить соединения
        logger.warning("create_pool() вызван повторно: пул уже существует")
        return _pool

    dsn = DB_URL
    _pool = await asyncpg.create_pool(
        dsn,
        min_size=POOL_MIN_SIZE,
        max_size=POOL_MAX_SIZE,
    )
    logger.info("Пул соединений PostgreSQL создан")
    return _pool


async def close_pool(pool: asyncpg.Pool) -> None:
    """
    Закрывает переданный пул соединений.

    Вызывается при остановке приложения, чтобы корректно освободить
    все соединения с базой данных.
    """
    global _pool

    await pool.close()
    _pool = None
    logger.info("Пул соединений PostgreSQL закрыт")


def get_pool() -> asyncpg.Pool:
    """
    Возвращает глобальный пул соединений.

    Использовать в любом месте кода, где нужен доступ к БД, но нет
    возможности (или смысла) пробрасывать пул через аргументы —
    например, внутри сервисов или планировщика задач.

    Вызывать только после create_pool(), иначе будет вызвано исключение.
    """
    if _pool is None:
        raise RuntimeError(
            "Пул соединений ещё не создан. "
            "Сначала вызовите create_pool() при старте приложения."
        )
    return _pool
