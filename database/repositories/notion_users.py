"""
Репозиторий кэша пользователей рабочего пространства Notion.

Хранит список участников Notion-workspace для конкретного Telegram-пользователя.
Используется при выборе assignee без повторных запросов к Notion API.
"""

from database.repositories.base import BaseRepository, DbConnection


class NotionWorkspaceRepository(BaseRepository):
    """
    Операции над таблицей notion_workspace_users.
    """

    def __init__(self, db: DbConnection) -> None:
        super().__init__(db)

    async def clear(self, tg_id: int) -> None:
        """Удаляет кэш участников Notion для указанного пользователя."""
        await self.db.execute(
            "DELETE FROM notion_workspace_users WHERE tg_id = $1",
            tg_id,
        )

    async def save_many(self, tg_id: int, users: list[dict]) -> None:
        """
        Пакетно сохраняет участников Notion в кэш.

        Используем unnest вместо executemany — это единственный круговой запрос
        к базе вместо N запросов, что на порядок быстрее при большом числе
        участников workspace.

        Каждый элемент users ожидается в формате:
            {"id": str, "name": str | None, "email": str | None}
        """
        if not users:
            return

        notion_user_ids = [u["id"] for u in users]
        names = [u.get("name") for u in users]
        emails = [u.get("email") for u in users]

        # unnest разворачивает три массива в строки одновременно —
        # одна инструкция INSERT вместо цикла по executemany
        await self.db.execute(
            """
            INSERT INTO notion_workspace_users (tg_id, notion_user_id, name, email)
            SELECT $1, uid, name, email
            FROM unnest(
                $2::text[],
                $3::text[],
                $4::text[]
            ) AS t(uid, name, email)
            ON CONFLICT (tg_id, notion_user_id) DO UPDATE
                SET name  = EXCLUDED.name,
                    email = EXCLUDED.email
            """,
            tg_id,
            notion_user_ids,
            names,
            emails,
        )

    async def get_cached(self, tg_id: int) -> list[dict]:
        """
        Возвращает закэшированных участников Notion для пользователя.

        Формат элементов: {"id": str, "name": str | None, "email": str | None}
        (совместим с форматом, который ожидает NotionApprovalHandler).
        """
        rows = await self.db.fetch(
            "SELECT notion_user_id, name, email FROM notion_workspace_users WHERE tg_id = $1",
            tg_id,
        )
        return [
            {
                "id": r["notion_user_id"],
                "name": r["name"],
                "email": r["email"],
            }
            for r in rows
        ]
