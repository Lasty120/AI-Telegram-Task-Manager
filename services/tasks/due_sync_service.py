
from aiosqlite import Connection, Row

from database.crud.task import (
    get_due_tasks_for_user,
    complete_all_due_tasks,
    get_active_tasks_with_notion_id,
    complete_tasks_by_ids,
)
# Переиспользуем публичный фетчер вместо дублирования логики пагинации
from services.notion.fetch_service import fetch_all_notion_pages
from services.notion.client import NotionClient


class DueSyncService:
    """
    Сервис для синхронизации и массового завершения просроченных задач.

    Ответственность:
    - Получить просроченные задачи пользователя.
    - Завершить все просроченные задачи в локальной БД.
    - Синхронизировать статусы с Notion: если задача там уже «done»,
      а в локальной БД ещё активна — пометить её выполненной.
    """

    def __init__(self, db: Connection, user: Row):
        self.db = db
        self.user = user

    async def get_due_tasks(self) -> list[Row]:
        """Возвращает все активные просроченные задачи пользователя."""
        return await get_due_tasks_for_user(self.db, self.user["id"])

    async def complete_all_due(self) -> int:
        """Помечает все просроченные задачи пользователя как выполненные."""
        return await complete_all_due_tasks(self.db, self.user["id"])

    async def sync_completed_from_notion(self) -> int:
        """
        Синхронизация «завершённых в Notion» задач → локальная БД.

        Алгоритм:
        1. Берём активные задачи с notion_page_id из локальной БД.
        2. Загружаем все страницы Notion через общий фетчер (без дублирования).
        3. Задачи, у которых статус в Notion начинается на «done» — завершаем локально.

        Returns:
            Количество задач, автоматически завершённых после сверки с Notion.
        """
        notion_token = self.user["notion_token"]
        notion_db_id = self.user["notion_db_id"]

        if not notion_token or not notion_db_id:
            return 0

        # Берём активные задачи с привязкой к Notion
        local_tasks = await get_active_tasks_with_notion_id(self.db, self.user["id"])
        if not local_tasks:
            return 0

        # Строим словарь notion_page_id → local task_id для быстрого поиска
        page_id_to_task_id: dict[str, int] = {
            row["notion_page_id"]: row["id"]
            for row in local_tasks
            if row["notion_page_id"]
        }
        if not page_id_to_task_id:
            return 0

        # Загружаем все страницы из Notion — используем ОБЩИЙ фетчер,
        client = NotionClient(notion_token)
        all_pages = await fetch_all_notion_pages(client=client, notion_db_id=notion_db_id)

        # Строим словарь notion_page_id → page для быстрого поиска по страницам Notion
        notion_pages_by_id: dict[str, dict] = {
            page.get("id", "").replace("-", ""): page
            for page in all_pages
        }

        # Итерируемся по локальным задачам:
        # завершаем, если задача done в Notion ИЛИ её нет в Notion вовсе
        tasks_to_complete = []
        for notion_page_id, task_id in page_id_to_task_id.items():
            page = notion_pages_by_id.get(notion_page_id)
            if page is None or _is_page_done(page):
                tasks_to_complete.append(task_id)

        if not tasks_to_complete:
            return 0

        return await complete_tasks_by_ids(self.db, tasks_to_complete)


def _is_page_done(page: dict) -> bool:
    """
    Проверяет, является ли страница Notion «выполненной»:
    статус начинается на «done» (регистронезависимо).

    Вынесена на уровень модуля (не метод класса), т.к. не использует self
    и потенциально может переиспользоваться в других местах.
    """
    properties = page.get("properties", {})
    for prop in properties.values():
        prop_type = prop.get("type")
        if prop_type in ("status", "select"):
            inner = prop.get(prop_type) or {}
            name = (inner.get("name") or "").strip().lower()
            if name.startswith("done"):
                return True
    return False