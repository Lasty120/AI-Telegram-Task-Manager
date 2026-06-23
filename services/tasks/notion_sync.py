from aiosqlite import Connection, Row

from messages import NotionMessages, TaskMessages
from database.schemas import TaskActionSchema
from utils.action_result import ActionResult
from services.notion.service import add_tasks_to_notion, sync_task_status
from database.crud.task import get_tasks_by_ids, set_task_notion_page_id, mark_tasks_notion_added
from database.crud.task import update_task

class NotionSyncService:
    """
    Сервис для синхронизации задач пользователя с Notion API.
    Предоставляет методы для добавления задач и синхронизации их статуса.
    """

    def __init__(self, db: Connection, user: Row):
        """
        Инициализирует сервис Notion.
        
        Args:
            db (Connection): Соединение с базой данных SQLite.
            user (Row): Запись пользователя из БД.
        """
        self.db = db
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
        # 1. Проверяем, настроена ли интеграция с Notion у пользователя
        notion_token = self.user["notion_token"]
        notion_db_id = self.user["notion_db_id"]

        if not notion_token or not notion_db_id:
            return ActionResult(text=NotionMessages.not_configured())

        # 2. Проверяем наличие переданных ID задач
        if not command.task_ids:
            return ActionResult(text=NotionMessages.no_tasks_to_send())

        # 3. Загружаем задачи из локальной базы данных
        tasks = await get_tasks_by_ids(
            db=self.db,
            task_ids=command.task_ids,
            user_id=self.user["id"],
        )

        if not tasks:
            return ActionResult(text=TaskMessages.task_not_found())

        # Определение приоритетов для статуса и мультиселекта
        resolved_tasks = []
        for task in tasks:
            task_dict = dict(task)
            
            # Приоритет: ИИ -> Локальная БД -> Настройки пользователя
            task_status = command.status or task_dict.get("notion_status") or self.user["notion_status_created"]
            task_ms = command.multi_select or task_dict.get("notion_multi_select")
            
            # Сохраняем обновленные значения в локальной базе данных
            await update_task(
                db=self.db,
                task_id=task_dict["id"],
                notion_status=task_status,
                notion_multi_select=task_ms
            )
            
            task_dict["notion_status"] = task_status
            task_dict["notion_multi_select"] = task_ms
            resolved_tasks.append(task_dict)

        # 4. Отправляем задачи в Notion через API-интеграцию
        notion_user_id = self.user["notion_user_id"] if "notion_user_id" in self.user.keys() else None
        success_count, errors, page_ids = await add_tasks_to_notion(
            notion_token=notion_token,
            notion_db_id=notion_db_id,
            tasks=resolved_tasks,
            notion_user_id=notion_user_id,
        )

        # 5. Сохраняем полученные page_id для каждой созданной страницы в Notion
        for tid, pid in page_ids.items():
            await set_task_notion_page_id(self.db, tid, pid)

        # 6. Отмечаем задачи в локальной базе как успешно добавленные в Notion
        if success_count > 0:
            added_ids = list(page_ids.keys())
            await mark_tasks_notion_added(self.db, added_ids)

        # 7. Возвращаем результат отправки со статусом и возможными ошибками
        return ActionResult(
            text=NotionMessages.tasks_sent(
                success_count=success_count,
                total=len(tasks),
                errors=errors,
            )
        )

    async def sync_task_status_to_notion(self, task: Row, status: str):
        """
        Отправляет обновление статуса задачи в Notion (например, "complete").
        
        Args:
            task (Row): Запись задачи из БД.
            status (str): Новый статус задачи.
        """
        await sync_task_status(self.user, task, status)

    async def add_single_task_to_notion(self, task: Row) -> bool:
        """
        Вспомогательный метод для автоматического добавления одной свежесозданной задачи в Notion.
        
        Args:
            task (Row): Новая задача.
            
        Returns:
            bool: True, если задача успешно добавлена в Notion, иначе False.
        """
        user_dict = dict(self.user)
        notion_token = user_dict.get("notion_token")
        notion_db_id = user_dict.get("notion_db_id")

        if not notion_token or not notion_db_id:
            return False

        # Отправляем одну задачу в Notion
        notion_user_id = user_dict.get("notion_user_id")
        success_count, _, page_ids = await add_tasks_to_notion(
            notion_token=notion_token,
            notion_db_id=notion_db_id,
            tasks=[dict(task)],
            notion_user_id=notion_user_id,
        )

        # Если успешно, сохраняем page_id
        if task['id'] in page_ids:
            await set_task_notion_page_id(self.db, task['id'], page_ids[task['id']])
            return True

        return False
