"""
services/tasks/due_sync_service.py

Сервис синхронизации и массового завершения просроченных задач.
Изменения (Этап 4):
  - db: Connection заменён на task_repo: TaskRepository (инъекция зависимостей).
  - Все прямые вызовы database.crud.task.* заменены на методы task_repo.
"""

# Репозиторий задач вместо прямых CRUD-функций
from database.repositories import TaskRepository

# Переиспользуем публичный фетчер страниц Notion (без дублирования логики пагинации)
from services.notion.fetch_service import fetch_all_notion_pages
from services.notion.client import NotionClient


class DueSyncService:
    """
    Сервис для синхронизации и массового завершения просроченных задач.

    Ответственность:
    - Получить просроченные задачи пользователя.
    - Завершить все просроченные задачи в репозитории.
    - Синхронизировать статусы с Notion: если задача там уже «done»,
      а в репозитории ещё активна — пометить её выполненной.
    """

    def __init__(self, task_repo: TaskRepository, user: dict):
        """
        Инициализирует сервис синхронизации просроченных задач.

        Args:
            task_repo (TaskRepository): Репозиторий задач (asyncpg).
            user (dict): Словарь пользователя из БД.
        """
        self.task_repo = task_repo
        self.user = user

    async def get_due_tasks(self) -> list[dict]:
        """Возвращает все активные просроченные задачи пользователя."""
        return await self.task_repo.get_due(user_id=self.user["id"])

    async def complete_all_due(self) -> int:
        """Помечает все просроченные задачи пользователя как выполненные.

        Returns:
            int: Количество завершённых задач.
        """
        return await self.task_repo.complete_all_due(user_id=self.user["id"])

    async def sync_completed_from_notion(self) -> int:
        """
        Синхронизация «завершённых в Notion» задач → репозиторий.

        Алгоритм:
        1. Берём активные задачи с notion_page_id из репозитория.
        2. Загружаем все страницы Notion через общий фетчер (без дублирования).
        3. Задачи, у которых статус в Notion начинается на «done» — завершаем локально.

        Returns:
            int: Количество задач, автоматически завершённых после сверки с Notion.
        """
        notion_token = self.user.get("notion_token")
        notion_db_id = self.user.get("notion_db_id")

        if not notion_token or not notion_db_id:
            return 0

        # Получаем активные задачи с notion_page_id через репозиторий
        local_tasks = await self.task_repo.get_active_with_notion_id(user_id=self.user["id"])
        if not local_tasks:
            return 0

        # Нормализуем ID с обеих сторон, чтобы форматы (с дефисами/без)
        # не приводили к ложному «страница не найдена»
        page_id_to_task_id: dict[str, int] = {
            _normalize_page_id(task["notion_page_id"]): task["id"]
            for task in local_tasks
            if task.get("notion_page_id")
        }
        if not page_id_to_task_id:
            return 0

        client = NotionClient(notion_token)
        all_pages = await fetch_all_notion_pages(client=client, notion_db_id=notion_db_id)

        notion_pages_by_id: dict[str, dict] = {
            _normalize_page_id(page.get("id", "")): page
            for page in all_pages
        }

        tasks_to_complete = []
        for notion_page_id, task_id in page_id_to_task_id.items():
            page = notion_pages_by_id.get(notion_page_id)
            # Страница удалена в Notion или статус — «done»
            if page is None or _is_page_done(page):
                tasks_to_complete.append(task_id)

        if not tasks_to_complete:
            return 0

        # Массово завершаем задачи через репозиторий
        return await self.task_repo.complete_by_ids(tasks_to_complete)


def _normalize_page_id(page_id: str) -> str:
    """Убирает дефисы, чтобы сравнивать ID Notion независимо от формата хранения."""
    return (page_id or "").replace("-", "")


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