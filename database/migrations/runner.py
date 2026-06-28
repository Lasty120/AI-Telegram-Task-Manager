"""
Раннер миграций для PostgreSQL.

Заменяет старую логику "безопасной автомиграции" из database/init_db.py
(там колонки добавлялись через ручные ALTER TABLE с проверкой
PRAGMA table_info). Теперь схема версионируется обычными SQL-файлами
в папке migrations/, а раннер сам решает, какие из них ещё не применены.

Принцип работы:
1. Гарантируем существование служебной таблицы schema_migrations.
2. Читаем *.sql файлы из этой папки, сортируем по имени (числовой префикс
   001_, 002_, ... задаёт порядок применения).
3. Каждый файл, имени которого нет в schema_migrations, оборачиваем
   в транзакцию: выполняем SQL и сразу же записываем имя файла как
   применённое — если что-то упадёт, ни SQL, ни запись не сохранятся.
"""

import logging
from pathlib import Path

import asyncpg

logger = logging.getLogger(__name__)

# Папка, где лежат файлы миграций (рядом с этим файлом)
MIGRATIONS_DIR = Path(__file__).parent

_CREATE_MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    name TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def _get_migration_files() -> list[Path]:
    """Возвращает список файлов миграций, отсортированный по имени."""
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


async def run_migrations(pool: asyncpg.Pool) -> None:
    """
    Применяет все ещё не применённые миграции из папки migrations/.

    Вызывается один раз при старте приложения, сразу после создания
    пула соединений (create_pool), до начала обработки обновлений бота.
    """
    async with pool.acquire() as connection:
        await connection.execute(_CREATE_MIGRATIONS_TABLE)

        applied_rows = await connection.fetch("SELECT name FROM schema_migrations")
        applied_names = {row["name"] for row in applied_rows}

        migration_files = _get_migration_files()
        if not migration_files:
            logger.warning("Папка migrations/ не содержит ни одного .sql файла")
            return

        for migration_file in migration_files:
            migration_name = migration_file.name

            if migration_name in applied_names:
                logger.info("Миграция %s уже применена, пропускаем", migration_name)
                continue

            sql = migration_file.read_text(encoding="utf-8")

            # Выполняем SQL миграции и отметку о применении в одной транзакции:
            # либо применяется и фиксируется целиком, либо не применяется вовсе
            async with connection.transaction():
                await connection.execute(sql)
                await connection.execute(
                    "INSERT INTO schema_migrations (name) VALUES ($1)",
                    migration_name,
                )

            logger.info("Миграция %s применена", migration_name)
