"""
Репозиторий пользователей.

Инкапсулирует все SQL-операции над таблицей users в asyncpg-стиле.
"""

from database.repositories.base import BaseRepository, DbConnection


class UserRepository(BaseRepository):
    """
    CRUD-операции над таблицей users.
    """

    def __init__(self, db: DbConnection) -> None:
        super().__init__(db)

    async def get_by_tg_id(self, tg_id: int) -> dict | None:
        """Возвращает пользователя по tg_id или None."""
        row = await self.db.fetchrow(
            "SELECT * FROM users WHERE tg_id = $1",
            tg_id,
        )
        return dict(row) if row else None

    async def create(self, tg_id: int, lang: str = "ru") -> dict | None:
        """
        Создаёт пользователя, если его ещё нет (ON CONFLICT DO NOTHING).
        Возвращает запись пользователя или None при конфликте.

        RETURNING * позволяет получить запись без отдельного SELECT.
        """
        row = await self.db.fetchrow(
            """
            INSERT INTO users (tg_id, lang)
            VALUES ($1, $2)
            ON CONFLICT (tg_id) DO NOTHING
            RETURNING *
            """,
            tg_id, lang,
        )
        return dict(row) if row else None

    async def update_lang(self, tg_id: int, lang: str) -> None:
        """Обновляет язык интерфейса пользователя."""
        await self.db.execute(
            "UPDATE users SET lang = $1 WHERE tg_id = $2",
            lang, tg_id,
        )

    async def update_notion(
        self,
        tg_id: int,
        notion_token: str | None = None,
        notion_db_id: str | None = None,
        notion_status_notified: str | None = None,
        notion_status_completed: str | None = None,
        notion_status_created: str | None = None,
        notion_statuses: str | None = None,
        notion_multi_selects: str | None = None,
    ) -> None:
        """
        Обновляет настройки интеграции с Notion.
        Сбрасывает notion_user_id и notion_user_name в NULL —
        они устанавливаются отдельно через approve_pending_notion.
        """
        await self.db.execute(
            """
            UPDATE users
            SET notion_token            = $1,
                notion_db_id            = $2,
                notion_status_notified  = $3,
                notion_status_completed = $4,
                notion_status_created   = $5,
                notion_statuses         = $6,
                notion_multi_selects    = $7,
                notion_user_id          = NULL,
                notion_user_name        = NULL
            WHERE tg_id = $8
            """,
            notion_token,
            notion_db_id,
            notion_status_notified,
            notion_status_completed,
            notion_status_created,
            notion_statuses,
            notion_multi_selects,
            tg_id,
        )

    async def update_pending_notion(
        self,
        tg_id: int,
        pending_id: str,
        pending_name: str,
    ) -> None:
        """
        Сохраняет временные данные (ожидающие одобрения) пользователя Notion.
        Финальный перенос в основные колонки — через approve_pending_notion.
        """
        await self.db.execute(
            """
            UPDATE users
            SET pending_notion_user_id   = $1,
                pending_notion_user_name = $2
            WHERE tg_id = $3
            """,
            pending_id, pending_name, tg_id,
        )

    async def approve_pending_notion(self, tg_id: int) -> None:
        """
        Атомарно переносит pending-данные в основные колонки Notion
        и очищает временные поля. Одна операция — нет риска гонки.
        """
        await self.db.execute(
            """
            UPDATE users
            SET notion_user_id           = pending_notion_user_id,
                notion_user_name         = pending_notion_user_name,
                pending_notion_user_id   = NULL,
                pending_notion_user_name = NULL
            WHERE tg_id = $1
            """,
            tg_id,
        )

    async def reject_pending_notion(self, tg_id: int) -> None:
        """Очищает временные pending-данные без переноса в основные колонки."""
        await self.db.execute(
            """
            UPDATE users
            SET pending_notion_user_id   = NULL,
                pending_notion_user_name = NULL
            WHERE tg_id = $1
            """,
            tg_id,
        )

    async def get_all(self) -> list[dict]:
        """
        Возвращает всех пользователей.
        Используется планировщиком для рассылки уведомлений.
        """
        rows = await self.db.fetch("SELECT * FROM users")
        return [dict(r) for r in rows]
