"""
services/tasks/notion_sync.py

Сервис синхронизации задач с Notion.
Изменения (Этап 4):
  - db: Connection заменён на task_repo: TaskRepository (инъекция зависимостей).
  - Все прямые вызовы database.crud.task заменены на методы task_repo.
"""

# Импорт репозитория задач вместо прямых CRUD-функций
from database.repositories import TaskRepository

# Импорт сообщений бота (мультиязычность)
from messages import NotionMessages, TaskMessages, NotionCommentMessages
from database.schemas import TaskActionSchema
from utils.action_result import ActionResult
from utils.formatters import capitalize_first

# Сервисы Notion API
from services.notion.service import (
    add_tasks_to_notion,
    sync_task_status,
    add_comment_to_notion_page,
)


class NotionSyncService:
    """
    Сервис для синхронизации задач пользователя с Notion API.
    Предоставляет методы для добавления задач, синхронизации статусов
    и добавления комментариев к страницам Notion.
    """

    def __init__(self, task_repo: TaskRepository, user: dict):
        """
        Инициализирует сервис Notion.

        Args:
            task_repo (TaskRepository): Репозиторий задач (asyncpg).
            user (dict): Словарь пользователя из БД.
        """
        self.task_repo = task_repo
        self.user = user

    async def add_to_notion(self, command: TaskActionSchema) -> ActionResult:
        """
        Экшен-метод для массовой отправки списка выбранных задач в Notion.
        Используется в ответ на команду пользователя.

        Args:
            command (TaskActionSchema): Параметры команды с идентификаторами задач.

        Returns:
            ActionResult: Результат выполнения операции с текстовым подтверждением.
        """
        # Проверяем, настроена ли интеграция с Notion у пользователя
        notion_token = self.user.get("notion_token")
        notion_db_id = self.user.get("notion_db_id")

        if not notion_token or not notion_db_id:
            return ActionResult(text=NotionMessages.not_configured())

        # Проверяем наличие переданных ID задач
        if not command.task_ids:
            return ActionResult(text=NotionMessages.no_tasks_to_send())

        # Загружаем задачи из репозитория
        tasks = await self.task_repo.get_by_ids(
            user_id=self.user["id"],
            ids=command.task_ids,
        )

        if not tasks:
            return ActionResult(text=TaskMessages.task_not_found())

        # Разрешаем приоритеты статуса и мультиселекта для каждой задачи:
        # приоритет: команда ИИ → локальная БД → настройки пользователя
        resolved_tasks = []
        for task in tasks:
            task_dict = dict(task)

            task_status = (
                command.status
                or task_dict.get("notion_status")
                or self.user.get("notion_status_created")
            )
            task_ms = command.multi_select or task_dict.get("notion_multi_select")

            # Сохраняем обновлённые значения в репозитории
            await self.task_repo.update(
                task_dict["id"],
                notion_status=task_status,
                notion_multi_select=task_ms,
            )

            task_dict["notion_status"] = task_status
            task_dict["notion_multi_select"] = task_ms
            resolved_tasks.append(task_dict)

        # Отправляем задачи в Notion через API-интеграцию
        notion_user_id = self.user.get("notion_user_id")
        success_count, errors, page_ids = await add_tasks_to_notion(
            notion_token=notion_token,
            notion_db_id=notion_db_id,
            tasks=resolved_tasks,
            notion_user_id=notion_user_id,
        )

        # Сохраняем полученные page_id для каждой созданной страницы в Notion
        for tid, pid in page_ids.items():
            await self.task_repo.set_notion_page_id(tid, pid)

        # Отмечаем задачи в репозитории как успешно добавленные в Notion
        if success_count > 0:
            added_ids = list(page_ids.keys())
            await self.task_repo.mark_notion_added(added_ids)

        # Возвращаем результат отправки со статусом и возможными ошибками
        return ActionResult(
            text=NotionMessages.tasks_sent(
                success_count=success_count,
                total=len(tasks),
                errors=errors,
            )
        )

    async def add_comment_to_notion(self, command: TaskActionSchema) -> ActionResult:
        """
        Добавляет текстовый комментарий к странице задачи в Notion.

        Выполняет полную цепочку валидаций:
          - Проверяет наличие Notion-интеграции у пользователя.
          - Определяет task_id из команды ИИ.
          - Загружает задачу из репозитория.
          - Проверяет права доступа пользователя.
          - Убеждается, что задача уже добавлена в Notion (есть notion_page_id).
          - Проверяет наличие текста комментария.

        Args:
            command (TaskActionSchema): Схема команды с полями task_id и comment_text.

        Returns:
            ActionResult: Результат операции с текстом ответа для пользователя.
        """
        # Проверяем настройку интеграции с Notion
        notion_token = self.user.get("notion_token")
        notion_db_id = self.user.get("notion_db_id")

        if not notion_token or not notion_db_id:
            return ActionResult(text=NotionCommentMessages.not_configured())

        # Определяем ID задачи (task_id имеет приоритет над первым из task_ids)
        task_id = command.task_id or (command.task_ids[0] if command.task_ids else None)
        if not task_id:
            return ActionResult(text=NotionCommentMessages.task_id_missing())

        # Загружаем задачу из репозитория
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            return ActionResult(text=TaskMessages.task_not_found())

        # Проверяем права доступа: комментировать можно только свои задачи
        if task["user_id"] != self.user["id"]:
            return ActionResult(text=NotionCommentMessages.task_access_denied())

        # Убеждаемся, что задача уже экспортирована в Notion и имеет page_id
        page_id = task.get("notion_page_id")
        if not page_id:
            return ActionResult(text=NotionCommentMessages.page_not_found())

        # Проверяем наличие и непустоту текста комментария
        comment_text = command.comment_text
        if not comment_text or not comment_text.strip():
            return ActionResult(text=NotionCommentMessages.comment_text_missing())

        # Первая буква комментария всегда заглавная — нормализуем перед отправкой
        normalized_comment = capitalize_first(comment_text.strip())

        # Вызываем API Notion для создания комментария на странице
        success = await add_comment_to_notion_page(
            notion_token=notion_token,
            page_id=page_id,
            comment_text=normalized_comment,
        )

        if success:
            return ActionResult(text=NotionCommentMessages.comment_added(task["content"]))

        return ActionResult(text=NotionCommentMessages.comment_failed())

    async def sync_task_status_to_notion(self, task: dict, status: str) -> None:
        """
        Отправляет обновление статуса задачи в Notion (например, "complete").

        Args:
            task (dict): Словарь задачи из БД.
            status (str): Новый статус задачи.
        """
        await sync_task_status(self.user, task, status)

    async def update_task_in_notion(self, task: dict) -> bool:
        """
        Обновляет параметры существующей задачи в Notion, если задача ранее
        была успешно добавлена (notion_added = 1).

        Args:
            task (dict): Словарь задачи из репозитория.

        Returns:
            bool: True, если обновление выполнено успешно, иначе False.
        """
        if not task.get("notion_added") or not task.get("notion_page_id"):
            return False

        notion_token = self.user.get("notion_token")
        notion_db_id = self.user.get("notion_db_id")

        if not notion_token or not notion_db_id:
            return False

        notion_user_id = self.user.get("notion_user_id")

        from services.notion.service import update_page_in_notion
        return await update_page_in_notion(
            notion_token=notion_token,
            notion_db_id=notion_db_id,
            page_id=task["notion_page_id"],
            task_dict=task,
            notion_user_id=notion_user_id,
        )

    async def add_single_task_to_notion(self, task: dict) -> bool:
        """
        Вспомогательный метод для автоматического добавления одной
        свежесозданной задачи в Notion.

        Args:
            task (dict): Словарь новой задачи.

        Returns:
            bool: True, если задача успешно добавлена в Notion, иначе False.
        """
        notion_token = self.user.get("notion_token")
        notion_db_id = self.user.get("notion_db_id")

        if not notion_token or not notion_db_id:
            return False

        notion_user_id = self.user.get("notion_user_id")
        success_count, _, page_ids = await add_tasks_to_notion(
            notion_token=notion_token,
            notion_db_id=notion_db_id,
            tasks=[task],
            notion_user_id=notion_user_id,
        )

        # Если успешно, сохраняем page_id через репозиторий
        if task["id"] in page_ids:
            await self.task_repo.set_notion_page_id(task["id"], page_ids[task["id"]])
            return True

        return False
