from datetime import datetime
from aiogram import Bot
from aiosqlite import Connection, Row

from messages import TaskMessages
from database.schemas import TaskActionSchema
from database.crud.task import (
    create_task, get_task_by_id, get_tasks_by_ids, update_task, complete_task, save_user_search
)
from keyboards.reply_keyboards import get_main_kb
from keyboards.inline_keyboards import get_pagination_keyboard
from utils.context import user_lang
from config import TIMEZONE, TASKS_LIMIT_OF_PAGES
from utils.formatters import get_display_end_time
from utils.action_result import ActionResult

from services.tasks.conflict import ConflictService
from services.tasks.scheduler import SchedulerService
from services.tasks.notion_sync import NotionSyncService
from keyboards.inline_keyboards import get_conflict_resolution_keyboard


class TaskCRUDService:
    """
    Сервис для выполнения CRUD операций (создание, чтение/поиск, обновление, выполнение) с задачами.
    Координирует действия с планировщиком (SchedulerService), сервисом Notion (NotionSyncService)
    и проверкой конфликтов (ConflictService).
    """

    def __init__(
        self,
        db: Connection,
        user: Row,
        bot: Bot,
        conflict_service: ConflictService,
        scheduler_service: SchedulerService,
        notion_service: NotionSyncService
    ):
        """
        Инициализирует CRUD-сервис со всеми необходимыми зависимостями.
        
        Args:
            db (Connection): Соединение с БД.
            user (Row): Запись пользователя.
            bot (Bot): Экземпляр бота Telegram.
            conflict_service (ConflictService): Зависимость для управления коллизиями времени.
            scheduler_service (SchedulerService): Зависимость планировщика уведомлений.
            notion_service (NotionSyncService): Зависимость для синхронизации с Notion.
        """
        self.db = db
        self.user = user
        self.bot = bot
        self.tz = TIMEZONE
        self.conflict_service = conflict_service
        self.scheduler_service = scheduler_service
        self.notion_service = notion_service

    async def create(self, command: TaskActionSchema) -> ActionResult:
        """
        Создает новую задачу в базе данных, планирует уведомления и обрабатывает коллизии времени.
        
        Args:
            command (TaskActionSchema): Параметры новой задачи.
            
        Returns:
            ActionResult: Подтверждение создания (или предупреждение о конфликте времени).
        """
        # 1. Определяем время начала задачи
        if not command.time:
            # Если время не указано, автоматически находим первый свободный слот
            localized_dt = await self.conflict_service.find_first_free_slot(command.duration)
            task_timestamp = int(localized_dt.timestamp())
            display_time = localized_dt.strftime("%Y-%m-%d %H:%M")
        else:
            # Парсим указанное пользователем время
            try:
                naive_dt = datetime.strptime(command.time, "%Y-%m-%d %H:%M")
                localized_dt = self.tz.localize(naive_dt)
                task_timestamp = int(localized_dt.timestamp())
                display_time = command.time
            except Exception:
                return ActionResult(text=TaskMessages.invalid_time_format())

        # Разрешаем статус и мультиселект для Notion
        notion_status = command.status or self.user["notion_status_created"]
        notion_multi_select = command.multi_select

        # 2. Создаем запись о задаче в локальной БД
        new_task_id = await create_task(
            db=self.db,
            user_id=self.user['id'],
            time=task_timestamp,
            content=command.content,
            details=command.details,
            duration=command.duration,
            importance=command.importance,
            notion_status=notion_status,
            notion_multi_select=notion_multi_select,
        )

        # 3. Добавляем уведомление о задаче в планировщик
        self.scheduler_service.update_scheduler_jobs(
            task_id=new_task_id,
            content=command.content,
            details=command.details,
            localized_dt=localized_dt,
            duration=command.duration,
            importance=command.importance,
        )

        # 4. Проверяем на наличие временных конфликтов
        conflict_task = None
        if command.time:
            conflict_task = await self.conflict_service.check_conflict(
                task_timestamp, command.duration, exclude_task_id=new_task_id
            )

        # 5. Если обнаружен конфликт, возвращаем интерактивную форму для разрешения коллизии
        if conflict_task:

            warning_text = TaskMessages.conflict_warning(
                new_task_content=command.content,
                new_task_time=display_time,
                old_task_content=conflict_task['content'],
                old_task_time=datetime.fromtimestamp(
                    conflict_task['time'], self.tz
                ).strftime("%Y-%m-%d %H:%M")
            )
            kb = get_conflict_resolution_keyboard(
                old_task_id=conflict_task['id'],
                new_task_id=new_task_id,
                old_task_content=conflict_task['content'],
                new_task_content=command.content,
                add_to_notion=command.add_to_notion
            )
            return ActionResult(text=warning_text, keyboard=kb, send_separately=True)

        # 6. Если конфликтов нет, формируем обычное подтверждение и синхронизируем с Notion при необходимости
        display_end_time = get_display_end_time(localized_dt, command.duration)
        confirm_text = TaskMessages.task_created(
            content=command.content,
            display_time=display_time,
            details=command.details,
            display_end_time=display_end_time,
            importance=command.importance,
        )

        # Синхронизация с Notion (если пользователь явно запросил add_to_notion)
        if command.add_to_notion:
            new_task = await get_task_by_id(self.db, new_task_id)
            if new_task:
                await self.notion_service.add_single_task_to_notion(new_task)

        return ActionResult(text=confirm_text, task_time=command.time)

    async def update(self, command: TaskActionSchema) -> ActionResult:
        """
        Обновляет параметры существующей задачи в БД и обновляет её в планировщике.
        
        Args:
            command (TaskActionSchema): Параметры изменения.
            
        Returns:
            ActionResult: Подтверждение обновления.
        """
        task_id = command.task_id or (command.task_ids[0] if command.task_ids else None)
        if not task_id:
            return ActionResult(text=TaskMessages.task_update_id_missing())

        task = await get_task_by_id(self.db, task_id)
        if not task:
            return ActionResult(text=TaskMessages.task_not_found())

        # Защита: редактировать можно только свои задачи
        if task['user_id'] != self.user['id']:
            return ActionResult(text=TaskMessages.task_update_access_denied())

        new_content = command.content if command.content is not None else task['content']
        new_details = command.details if command.details is not None else task['details']
        new_time_timestamp = task['time']
        display_time = datetime.fromtimestamp(task['time'], self.tz).strftime("%Y-%m-%d %H:%M")

        # Пересчитываем время начала при необходимости
        if command.time is not None:
            try:
                naive_dt = datetime.strptime(command.time, "%Y-%m-%d %H:%M")
                localized_dt = self.tz.localize(naive_dt)
                new_time_timestamp = int(localized_dt.timestamp())
                display_time = command.time
            except Exception:
                return ActionResult(text=TaskMessages.invalid_update_time_format())
        else:
            localized_dt = datetime.fromtimestamp(new_time_timestamp, self.tz)

        new_duration = command.duration if command.duration is not None else (
            task['duration'] if 'duration' in task.keys() else None
        )
        new_importance = command.importance if command.importance is not None else (
            task['importance'] if 'importance' in task.keys() else None
        )

        # Сохраняем изменения в БД
        await update_task(
            db=self.db, task_id=task_id,
            content=new_content, details=new_details,
            time_val=new_time_timestamp, duration=new_duration, importance=new_importance,
            notion_status=command.status, notion_multi_select=command.multi_select,
        )
        
        # Обновляем задачу в планировщике
        self.scheduler_service.update_scheduler_jobs(
            task_id=task_id, content=new_content, details=new_details,
            localized_dt=localized_dt, duration=new_duration, importance=new_importance,
        )

        # Получаем обновленную версию задачи из БД для синхронизации
        updated_task = await get_task_by_id(self.db, task_id)
        if updated_task and "notion_added" in updated_task.keys() and updated_task["notion_added"] == 1:
            await self.notion_service.update_task_in_notion(updated_task)

        display_end_time = get_display_end_time(localized_dt, new_duration)
        confirm_text = TaskMessages.task_updated(
            content=new_content,
            display_time=display_time,
            details=new_details,
            display_end_time=display_end_time,
            importance=new_importance,
        )

        # Если статус был обновлен в команде, добавляем название статуса капсом
        if command.status is not None:
            confirm_text += TaskMessages.status_updated_notification(command.status)

        return ActionResult(text=confirm_text, task_time=command.time)

    async def select(self, command: TaskActionSchema) -> ActionResult:
        """
        Ищет задачи и выводит их список с пагинацией.
        
        Args:
            command (TaskActionSchema): Параметры поиска.
            
        Returns:
            ActionResult: Результаты поиска с кнопками навигации.
        """
        if not command.task_ids:
            return ActionResult(text=TaskMessages.search_empty())

        # Сохраняем историю поиска
        await save_user_search(
            db=self.db,
            user_id=self.user["id"],
            task_ids=command.task_ids,
            query=command.content or "поиск"
        )

        limit = TASKS_LIMIT_OF_PAGES
        total_count = len(command.task_ids)

        # Достаем первую страницу задач
        tasks = await get_tasks_by_ids(
            db=self.db, task_ids=command.task_ids,
            user_id=self.user["id"], limit=limit, offset=0
        )

        if not tasks:
            return ActionResult(text=TaskMessages.search_not_found(), task_time=command.time)

        response_text = TaskMessages.search_results(
            query=command.content or "поиск", tasks=tasks, tz=self.tz
        )

        # Если задач больше, чем лимит страницы, добавляем пагинацию
        if total_count > limit:
            lang = user_lang.get()
            page_word = "Page" if lang == "en" else "Страница"
            from_word = "of" if lang == "en" else "из"
            total_pages = (total_count + limit - 1) // limit
            response_text += f"\n\n<i>{page_word} 1 {from_word} {total_pages}</i>"

        kb = get_pagination_keyboard(total_count, 1, limit, "page_select")

        return ActionResult(
            text=response_text,
            keyboard=kb or get_main_kb(),
            send_separately=True,
            task_time=command.time
        )

    async def delete(self, command: TaskActionSchema) -> ActionResult:
        """
        Завершает (удаляет) указанные задачи, стирая напоминания и обновляя статус в Notion.
        
        Args:
            command (TaskActionSchema): Запрос на удаление.
            
        Returns:
            ActionResult: Текст подтверждения выполнения.
        """
        task_ids = []
        if command.task_id:
            task_ids.append(command.task_id)
        if command.task_ids:
            for tid in command.task_ids:
                if tid not in task_ids:
                    task_ids.append(tid)

        if not task_ids:
            return ActionResult(text=TaskMessages.task_delete_id_missing())

        completed_titles = []
        not_found_count = 0
        denied_count = 0

        for tid in task_ids:
            task = await get_task_by_id(self.db, tid)
            if not task:
                not_found_count += 1
                continue
            if task['user_id'] != self.user['id']:
                denied_count += 1
                continue
                
            # Помечаем задачу как завершенную в локальной БД
            await complete_task(self.db, tid)
            # Удаляем ее из планировщика
            self.scheduler_service.remove_scheduler_jobs(tid)
            # Синхронизируем изменение с Notion
            await self.notion_service.sync_task_status_to_notion(task, "complete")
            completed_titles.append(task['content'])

        if not completed_titles:
            if denied_count > 0:
                return ActionResult(text=TaskMessages.task_delete_access_denied())
            elif not_found_count > 0:
                return ActionResult(text=TaskMessages.task_not_found())

        if len(completed_titles) == 1:
            return ActionResult(text=TaskMessages.task_completed(completed_titles[0]), task_time=command.time)
        else:
            return ActionResult(text=TaskMessages.tasks_completed_plural(completed_titles), task_time=command.time)
