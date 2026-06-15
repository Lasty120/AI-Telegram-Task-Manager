from datetime import datetime
from aiogram import Bot
from aiogram.types import Message
from aiosqlite import Connection, Row

from messages import TaskMessages
from database.schemas import TaskActionSchema
from database.crud.task import create_task, get_task_by_id, get_tasks_by_ids, update_task, complete_task, get_user_tasks, save_user_search
from keyboards.reply_keyboards import get_main_kb
from keyboards.inline_keyboards import get_pagination_keyboard
from utils.context import user_lang
from config import TIMEZONE, TASKS_LIMIT_OF_PAGES
from services.task_scheduler import TaskSchedulerService
from utils.formatters import get_display_end_time
from utils.action_result import ActionResult

from services.notion.service import add_tasks_to_notion, sync_task_status
from database.crud.task import get_task_by_id, mark_tasks_notion_added, set_task_notion_page_id

from messages import NotionMessages


class TaskActionsService:
    def __init__(self, db: Connection, user: Row, bot: Bot):
        self.db = db
        self.user = user
        self.bot = bot
        self.tz = TIMEZONE
        self.scheduler_service = TaskSchedulerService(bot=bot, user=user)

    async def _find_first_free_slot(self, duration_mins: int, exclude_task_id: int = None) -> datetime:
        """
        Находит первый свободный слот длительностью duration_mins начиная от текущего времени,
        который не перекрывается с другими активными задачами пользователя.
        """
        if not duration_mins:
            duration_mins = 30
            

        active_tasks = await get_user_tasks(self.db, self.user['id'])
        
        now = datetime.now(self.tz)
        candidate_start = now.replace(second=0, microsecond=0)
        
        intervals = []
        for task in active_tasks:
            if exclude_task_id and task['id'] == exclude_task_id:
                continue
            task_start = task['time']
            task_dur = task['duration'] if 'duration' in task.keys() and task['duration'] else 30
            task_end = task_start + task_dur * 60
            intervals.append((task_start, task_end))
            
        intervals.sort(key=lambda x: x[0])
        
        while True:
            candidate_start_ts = int(candidate_start.timestamp())
            candidate_end_ts = candidate_start_ts + duration_mins * 60
            
            overlap = False
            for start, end in intervals:
                if candidate_start_ts < end and candidate_end_ts > start:
                    overlap = True
                    candidate_start = datetime.fromtimestamp(end, self.tz)
                    break
                    
            if not overlap:
                return candidate_start

    async def _check_conflict(self, start_ts: int, duration_mins: int, exclude_task_id: int = None) -> Row | None:
        """
        Проверяет, перекрывается ли временной интервал [start_ts, start_ts + duration_mins * 60]
        с какими-либо существующими активными задачами пользователя.
        Возвращает первую конфликтующую задачу или None.
        """
        if not duration_mins:
            duration_mins = 30
            
        active_tasks = await get_user_tasks(self.db, self.user['id'])
        end_ts = start_ts + duration_mins * 60
        
        for task in active_tasks:
            if exclude_task_id and task['id'] == exclude_task_id:
                continue
            task_start = task['time']
            task_dur = task['duration'] if 'duration' in task.keys() and task['duration'] else 30
            task_end = task_start + task_dur * 60
            
            # Условие пересечения интервалов:
            if start_ts < task_end and end_ts > task_start:
                return task
        return None

    async def create(self, command: TaskActionSchema) -> ActionResult:
        if not command.time:
            localized_dt = await self._find_first_free_slot(command.duration)
            task_timestamp = int(localized_dt.timestamp())
            display_time = localized_dt.strftime("%Y-%m-%d %H:%M")
        else:
            try:
                naive_dt = datetime.strptime(command.time, "%Y-%m-%d %H:%M")
                localized_dt = self.tz.localize(naive_dt)
                task_timestamp = int(localized_dt.timestamp())
                display_time = command.time
            except Exception:
                return ActionResult(text=TaskMessages.invalid_time_format())

        new_task_id = await create_task(
            db=self.db,
            user_id=self.user['id'],
            time=task_timestamp,
            content=command.content,
            details=command.details,
            duration=command.duration,
            importance=command.importance,
        )

        self.scheduler_service.update_scheduler_jobs(
            task_id=new_task_id,
            content=command.content,
            details=command.details,
            localized_dt=localized_dt,
            duration=command.duration,
            importance=command.importance,
        )

        conflict_task = None
        if command.time:
            conflict_task = await self._check_conflict(
                task_timestamp, command.duration, exclude_task_id=new_task_id
            )

        if conflict_task:
            from keyboards.inline_keyboards import get_conflict_resolution_keyboard
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
                new_task_content=command.content
            )
            # Конфликт — всегда отдельно, потому что у него своя инлайн-клавиатура
            return ActionResult(text=warning_text, keyboard=kb, send_separately=True)
        else:
            display_end_time = get_display_end_time(localized_dt, command.duration)
            confirm_text = TaskMessages.task_created(
                content=command.content,
                display_time=display_time,
                details=command.details,
                display_end_time=display_end_time,
                importance=command.importance,
            )
            # Если пользователь попросил сразу добавить в Notion
            user_dict = dict(self.user)
            if command.add_to_notion and user_dict.get("notion_token") and user_dict.get("notion_db_id"):
                new_task = await get_task_by_id(self.db, new_task_id)
                if new_task:
                    success_count, _, page_ids = await add_tasks_to_notion(
                        notion_token=self.user["notion_token"],
                        notion_db_id=self.user["notion_db_id"],
                        tasks=[new_task],
                    )
                    if new_task_id in page_ids:
                        await set_task_notion_page_id(self.db, new_task_id, page_ids[new_task_id])

            return ActionResult(text=confirm_text, task_time=command.time)  # уже существующий return

    async def update(self, command: TaskActionSchema) -> ActionResult:
        task_id = command.task_id or (command.task_ids[0] if command.task_ids else None)
        if not task_id:
            return ActionResult(text=TaskMessages.task_update_id_missing())

        task = await get_task_by_id(self.db, task_id)
        if not task:
            return ActionResult(text=TaskMessages.task_not_found())

        if task['user_id'] != self.user['id']:
            return ActionResult(text=TaskMessages.task_update_access_denied())

        new_content = command.content if command.content is not None else task['content']
        new_details = command.details if command.details is not None else task['details']
        new_time_timestamp = task['time']
        display_time = datetime.fromtimestamp(task['time'], self.tz).strftime("%Y-%m-%d %H:%M")

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

        await update_task(
            db=self.db, task_id=task_id,
            content=new_content, details=new_details,
            time_val=new_time_timestamp, duration=new_duration, importance=new_importance,
        )
        self.scheduler_service.update_scheduler_jobs(
            task_id=task_id, content=new_content, details=new_details,
            localized_dt=localized_dt, duration=new_duration, importance=new_importance,
        )

        display_end_time = get_display_end_time(localized_dt, new_duration)
        confirm_text = TaskMessages.task_updated(
            content=new_content,
            display_time=display_time,
            details=new_details,
            display_end_time=display_end_time,
            importance=new_importance,
        )
        return ActionResult(text=confirm_text, task_time=command.time)


    async def select(self, command: TaskActionSchema) -> ActionResult:
        if not command.task_ids:
            return ActionResult(text=TaskMessages.search_empty())

        await save_user_search(
            db=self.db,
            user_id=self.user["id"],
            task_ids=command.task_ids,
            query=command.content or "поиск"
        )

        limit = TASKS_LIMIT_OF_PAGES
        total_count = len(command.task_ids)

        tasks = await get_tasks_by_ids(
            db=self.db, task_ids=command.task_ids,
            user_id=self.user["id"], limit=limit, offset=0
        )

        if not tasks:
            return ActionResult(text=TaskMessages.search_not_found(), task_time=command.time)

        response_text = TaskMessages.search_results(
            query=command.content or "поиск", tasks=tasks, tz=self.tz
        )

        if total_count > limit:
            lang = user_lang.get()
            page_word = "Page" if lang == "en" else "Страница"
            from_word = "of" if lang == "en" else "из"
            total_pages = (total_count + limit - 1) // limit
            response_text += f"\n\n📖 <i>{page_word} 1 {from_word} {total_pages}</i>"

        kb = get_pagination_keyboard(total_count, 1, limit, "page_select")

        # Select — всегда отдельно: у него своя пагинация и особый вид
        return ActionResult(
            text=response_text,
            keyboard=kb or get_main_kb(),
            send_separately=True,
            task_time=command.time
        )

    async def delete(self, command: TaskActionSchema) -> ActionResult:
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
            await complete_task(self.db, tid)
            self.scheduler_service.remove_scheduler_jobs(tid)
            await sync_task_status(self.user, task, "complete")
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

    async def add_to_notion(self, command: TaskActionSchema) -> ActionResult:


        # 1. Проверяем, настроен ли Notion у пользователя
        notion_token = self.user["notion_token"]
        notion_db_id = self.user["notion_db_id"]

        if not notion_token or not notion_db_id:
            return ActionResult(text=NotionMessages.not_configured())

        # 2. Получаем задачи по task_ids
        if not command.task_ids:
            return ActionResult(text=NotionMessages.no_tasks_to_send())

        tasks = await get_tasks_by_ids(
            db=self.db,
            task_ids=command.task_ids,
            user_id=self.user["id"],
        )

        if not tasks:
            return ActionResult(text=TaskMessages.task_not_found())

        # 3. Отправляем в Notion
        success_count, errors, page_ids = await add_tasks_to_notion(
            notion_token=notion_token,
            notion_db_id=notion_db_id,
            tasks=tasks,
        )

        for tid, pid in page_ids.items():
            await set_task_notion_page_id(self.db, tid, pid)

        # Помечаем успешно добавленные задачи
        if success_count > 0:
            from database.crud.task import mark_tasks_notion_added
            # Помечаем все task_ids — если были частичные ошибки,
            # лучше пометить все и дать пользователю повторить вручную
            added_ids = [
                t["id"] for t in tasks
            ][:success_count]  # первые success_count — оптимистично
            await mark_tasks_notion_added(self.db, added_ids)

        # 4. Формируем ответ
        return ActionResult(
            text=NotionMessages.tasks_sent(
                success_count=success_count,
                total=len(tasks),
                errors=errors,
            )
        )

    async def resolve_conflict(self, action: str, message: Message, new_task_id: int = None, old_task_id: int = None):
        """
        Разрешает конфликт между новой (new_task_id) и старой (old_task_id) задачами.
        """
        # 1. Быстрый выход для игнора (не дергаем базу лишний раз)
        if action == "ignore":
            # Используем метод из TaskMessages, если он там есть, или пишем текст напрямую
            await message.edit_text(
                TaskMessages.conflict_ignore(),
                parse_mode="HTML",
                reply_markup=None
            )
            return

        # 2. Получаем задачи из БД
        new_task = await get_task_by_id(self.db, new_task_id)
        old_task = await get_task_by_id(self.db, old_task_id)

        if not new_task or not old_task:
            await message.answer("⚠️ Ошибка: одна из конфликтующих задач не найдена.")
            return

        new_duration = new_task['duration'] if 'duration' in new_task.keys() and new_task['duration'] else 30
        old_duration = old_task['duration'] if 'duration' in old_task.keys() and old_task['duration'] else 30

        # 3. Определяем, кто двигается, а кто стоит на месте
        if action == "move_old":
            target_id, target_task, target_dur = old_task_id, old_task, old_duration
        else:  # move_new
            target_id, target_task, target_dur = new_task_id, new_task, new_duration

        # 4. Единая логика сдвига для выбранной задачи
        new_dt = await self._find_first_free_slot(target_dur, exclude_task_id=target_id)
        new_ts = int(new_dt.timestamp())

        await update_task(db=self.db, task_id=target_id, time_val=new_ts)
        self.scheduler_service.update_scheduler_jobs(
            task_id=target_id,
            content=target_task['content'],
            details=target_task['details'],
            localized_dt=new_dt,
            duration=target_dur,
            importance=target_task['importance'] if 'importance' in target_task.keys() else None
        )

        # 5. Формируем сообщение для UI
        new_dt_str = new_dt.strftime("%Y-%m-%d %H:%M")

        if action == "move_old":
            display_new_time = datetime.fromtimestamp(new_task['time'], self.tz).strftime("%Y-%m-%d %H:%M")
            msg_text = TaskMessages.conflict_resolved_move_old(
                new_title=new_task['content'],
                new_time=display_new_time,
                old_title=old_task['content'],
                old_new_time=new_dt_str
            )
        else:
            display_old_time = datetime.fromtimestamp(old_task['time'], self.tz).strftime("%Y-%m-%d %H:%M")
            msg_text = TaskMessages.conflict_resolved_move_new(
                new_title=new_task['content'],
                new_time=new_dt_str,
                old_title=old_task['content'],
                old_time=display_old_time
            )

        await message.edit_text(msg_text, parse_mode="HTML", reply_markup=None)