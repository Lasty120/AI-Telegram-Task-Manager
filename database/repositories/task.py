"""
Репозиторий задач.

Инкапсулирует все SQL-операции над таблицей tasks.
"""

import time
from typing import Any

from database.models import TaskStatus
from database.repositories.base import BaseRepository, DbConnection


class TaskRepository(BaseRepository):
    """
    CRUD-операции над таблицей tasks в asyncpg-стиле.
    """

    def __init__(self, db: DbConnection) -> None:
        super().__init__(db)

    # ------------------------------------------------------------------
    # Создание
    # ------------------------------------------------------------------

    async def create(
        self,
        content: str,
        time_val: int,
        user_id: int,
        details: str | None = None,
        duration: int | None = None,
        importance: str | None = None,
        notion_status: str | None = None,
        notion_multi_select: str | None = None,
    ) -> int:
        """
        Создаёт задачу и возвращает её id.
        RETURNING id — получаем id без отдельного SELECT.
        """
        row = await self.db.fetchrow(
            """
            INSERT INTO tasks
                (content, details, time, user_id, duration, importance,
                 notion_status, notion_multi_select)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
            """,
            content, details, time_val, user_id,
            duration, importance, notion_status, notion_multi_select,
        )
        return row["id"]

    # ------------------------------------------------------------------
    # Чтение одной записи
    # ------------------------------------------------------------------

    async def get_by_id(self, task_id: int) -> dict | None:
        """Возвращает задачу по id или None, если не найдена."""
        row = await self.db.fetchrow(
            "SELECT * FROM tasks WHERE id = $1",
            task_id,
        )
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Фетчинг задач
    # ------------------------------------------------------------------
    async def _fetch_paginated(
            self,
            where_clause: str,
            base_params: list[Any],
            limit: int | None = None,
            offset: int | None = None,
    ) -> list[dict]:
        """
        Общая логика для запросов с пагинацией.
        where_clause — часть SQL после WHERE (без слова WHERE).
        """
        query = f"SELECT * FROM tasks WHERE {where_clause} ORDER BY time ASC"
        params: list[Any] = list(base_params)

        if limit is not None:
            params.append(limit)
            query += f" LIMIT ${len(params)}"
        if offset is not None:
            params.append(offset)
            query += f" OFFSET ${len(params)}"

        rows = await self.db.fetch(query, *params)
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Активные задаачи
    # ------------------------------------------------------------------
    async def get_active(
        self,
        user_id: int,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict]:
        """
        Активные задачи пользователя с пагинацией.
        """
        return await self._fetch_paginated(
            "user_id = $1 AND status = $2",
            [user_id, TaskStatus.ACTIVE.value],
            limit,
            offset,
        )

    async def get_active_count(self, user_id: int) -> int:
        """Количество активных задач — для подсчёта страниц пагинации."""
        return await self.db.fetchval(
            "SELECT COUNT(*) FROM tasks WHERE user_id = $1 AND status = $2",
            user_id, TaskStatus.ACTIVE.value,
        )

    # ------------------------------------------------------------------
    # Выполненные задачи
    # ------------------------------------------------------------------

    async def get_completed(
        self,
        user_id: int,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict]:
        """Выполненные задачи пользователя с пагинацией."""
        return await self._fetch_paginated(
            "user_id = $1 AND status = $2",
            [user_id, TaskStatus.COMPLETED.value],
            limit,
            offset,
        )

    async def get_completed_count(self, user_id: int) -> int:
        """Количество выполненных задач пользователя."""
        return await self.db.fetchval(
            "SELECT COUNT(*) FROM tasks WHERE user_id = $1 AND status = $2",
            user_id, TaskStatus.COMPLETED.value,
        )

    # ------------------------------------------------------------------
    # Задачи по набору ID (поиск)
    # ------------------------------------------------------------------

    async def get_by_ids(
        self,
        user_id: int,
        ids: list[int],
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict]:
        """
        Возвращает задачи из заданного списка id для указанного пользователя.

        ANY($1::bigint[]) — безопасная альтернатива динамическому IN (?,?,?):
        передаём весь список одним параметром, PostgreSQL сам его разворачивает.
        """
        if not ids:
            return []
        return await self._fetch_paginated(
            "id = ANY($1::bigint[]) AND user_id = $2",
            [ids, user_id],
            limit, offset,
        )

    # ------------------------------------------------------------------
    # Просроченные задачи
    # ------------------------------------------------------------------

    async def get_due(self, user_id: int) -> list[dict]:
        """
        Активные задачи, у которых time <= текущему моменту.
        Используется для отображения в разделе «Просроченные».
        """
        current_time = int(time.time())
        rows = await self.db.fetch(
            """
            SELECT * FROM tasks
            WHERE user_id = $1 AND status = $2 AND time <= $3
            ORDER BY time ASC
            """,
            user_id, TaskStatus.ACTIVE.value, current_time,
        )
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Обновление
    # ------------------------------------------------------------------

    async def update(self, task_id: int, **kwargs: Any) -> None:
        """
        Динамический UPDATE по переданным именованным полям.

        Пример: await repo.update(task_id, content="Новый текст", time=1234567890)

        Нумерация плейсхолдеров начинается с $1 для первого поля,
        последний параметр $N — это task_id (WHERE id = $N).
        """
        # Список допустимых колонок для защиты от случайных инъекций через kwargs
        allowed_columns = {
            "content", "details", "time", "duration",
            "importance", "notion_status", "notion_multi_select",
        }

        updates: list[str] = []
        params: list[Any] = []

        for key, value in kwargs.items():
            if key not in allowed_columns or value is None:
                continue
            params.append(value)
            updates.append(f"{key} = ${len(params)}")

        if not updates:
            return

        # Последний параметр — task_id для WHERE
        params.append(task_id)
        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ${len(params)}"
        await self.db.execute(query, *params)

    async def complete(self, task_id: int) -> None:
        """Отмечает одну задачу как выполненную."""
        await self.db.execute(
            "UPDATE tasks SET status = $1 WHERE id = $2",
            TaskStatus.COMPLETED.value, task_id,
        )

    async def complete_all_due(self, user_id: int) -> int:
        """
        Массово завершает все просроченные активные задачи пользователя.
        Возвращает количество обновлённых записей.
        """
        current_time = int(time.time())
        result = await self.db.execute(
            """
            UPDATE tasks
            SET status = $1
            WHERE user_id = $2 AND status = $3 AND time <= $4
            """,
            TaskStatus.COMPLETED.value,
            user_id,
            TaskStatus.ACTIVE.value,
            current_time,
        )
        # asyncpg возвращает строку вида "UPDATE N" — парсим число
        return int(result.split()[-1])

    async def complete_by_ids(self, ids: list[int]) -> int:
        """
        Массово завершает задачи по списку id.
        ANY($1::bigint[]) — без динамических плейсхолдеров.
        Возвращает количество обновлённых записей.
        """
        if not ids:
            return 0

        result = await self.db.execute(
            "UPDATE tasks SET status = $1 WHERE id = ANY($2::bigint[])",
            TaskStatus.COMPLETED.value, ids,
        )
        return int(result.split()[-1])

    # ------------------------------------------------------------------
    # Notion-интеграция
    # ------------------------------------------------------------------

    async def get_active_with_notion_id(self, user_id: int) -> list[dict]:
        """
        Активные задачи с notion_page_id IS NOT NULL.
        Используется в DueSyncService для сверки с Notion.
        """
        rows = await self.db.fetch(
            """
            SELECT * FROM tasks
            WHERE user_id = $1 AND status = $2 AND notion_page_id IS NOT NULL
            ORDER BY time ASC
            """,
            user_id, TaskStatus.ACTIVE.value,
        )
        return [dict(r) for r in rows]

    async def get_existing_notion_page_ids(
        self,
        user_id: int,
        notion_page_ids: list[str],
    ) -> set[str]:
        """
        Возвращает набор notion_page_id, уже существующих в локальной БД.
        Используется для фильтрации дублей при импорте из Notion.
        """
        if not notion_page_ids:
            return set()

        rows = await self.db.fetch(
            """
            SELECT notion_page_id FROM tasks
            WHERE notion_page_id = ANY($1::text[]) AND user_id = $2
            """,
            notion_page_ids, user_id,
        )
        return {r["notion_page_id"] for r in rows if r["notion_page_id"]}

    async def set_notion_page_id(self, task_id: int, page_id: str) -> None:
        """Сохраняет ID страницы Notion и помечает задачу как добавленную."""
        await self.db.execute(
            "UPDATE tasks SET notion_added = 1, notion_page_id = $1 WHERE id = $2",
            page_id, task_id,
        )

    async def mark_notion_added(self, ids: list[int]) -> None:
        """
        Массово помечает задачи как добавленные в Notion (notion_added = 1).
        ANY($1::bigint[]) — нет динамических плейсхолдеров.
        """
        if not ids:
            return

        await self.db.execute(
            "UPDATE tasks SET notion_added = 1 WHERE id = ANY($1::bigint[])",
            ids,
        )

    async def mark_from_notion(self, task_id: int, notion_page_id: str) -> None:
        """
        Помечает задачу как импортированную из Notion:
        устанавливает notion_added=1 и сохраняет notion_page_id.
        """
        await self.db.execute(
            "UPDATE tasks SET notion_added = 1, notion_page_id = $1 WHERE id = $2",
            notion_page_id, task_id,
        )
