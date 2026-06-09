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
from config import TIMEZONE
from services.task_scheduler import TaskSchedulerService
from utils.formatters import get_display_end_time


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





    async def create(self, command: TaskActionSchema, message: Message):
        if not command.time:
            # Находим первый свободный временной слот в расписании
            localized_dt = await self._find_first_free_slot(command.duration)
            task_timestamp = int(localized_dt.timestamp())
            display_time = localized_dt.strftime("%Y-%m-%d %H:%M")
        else:
            # Парсим время, присланное ИИ
            try:
                naive_dt = datetime.strptime(command.time, "%Y-%m-%d %H:%M")
                localized_dt = self.tz.localize(naive_dt)
                task_timestamp = int(localized_dt.timestamp())
                display_time = command.time
            except Exception:
                await message.answer(TaskMessages.invalid_time_format())
                return

        # 1. Сохраняем в БД и получаем ID новой задачи
        new_task_id = await create_task(
            db=self.db,
            user_id=self.user['id'],  # Обращение как к Row (по ключу)
            time=task_timestamp,
            content=command.content,
            details=command.details,
            duration=command.duration,
            importance=command.importance,
        )

        # 2. Добавляем в планировщик на лету
        self.scheduler_service.update_scheduler_jobs(
            task_id=new_task_id,
            content=command.content,
            details=command.details,
            localized_dt=localized_dt,
            duration=command.duration,
            importance=command.importance,
        )

        # 3. Проверяем на конфликты с другими активными задачами (исключая саму новую задачу)
        conflict_task = None
        if command.time:
            conflict_task = await self._check_conflict(task_timestamp, command.duration, exclude_task_id=new_task_id)

        if conflict_task:
            # Отправляем предупреждение вместо обычной конфирмации
            from keyboards.inline_keyboards import get_conflict_resolution_keyboard
            
            warning_text = TaskMessages.conflict_warning(
                new_task_content=command.content,
                new_task_time=display_time,
                old_task_content=conflict_task['content'],
                old_task_time=datetime.fromtimestamp(conflict_task['time'], self.tz).strftime("%Y-%m-%d %H:%M")
            )
            
            kb = get_conflict_resolution_keyboard(
                old_task_id=conflict_task['id'],
                new_task_id=new_task_id,
                old_task_content=conflict_task['content'],
                new_task_content=command.content
            )
            await message.answer(warning_text, reply_markup=kb, parse_mode="HTML")
        else:
            display_end_time = get_display_end_time(localized_dt, command.duration)
            confirm_text = TaskMessages.task_created(
                content=command.content,
                display_time=display_time,
                details=command.details,
                duration=command.duration,
                display_end_time=display_end_time,
                importance=command.importance,
            )
            await message.answer(confirm_text, reply_markup=get_main_kb(), parse_mode="HTML")

    async def update(self, command: TaskActionSchema, message: Message):
        task_id = command.task_id or (command.task_ids[0] if command.task_ids else None)
        if not task_id:
            await message.answer(TaskMessages.task_update_id_missing())
            return

        # 1. Получаем задачу из базы данных
        task = await get_task_by_id(self.db, task_id)
        if not task:
            await message.answer(TaskMessages.task_not_found())
            return

        # Проверяем права: принадлежит ли задача текущему пользователю
        if task['user_id'] != self.user['id']:
            await message.answer(TaskMessages.task_update_access_denied())
            return

        # 2. Определяем обновленные значения
        # Контент
        new_content = command.content if command.content is not None else task['content']
        
        # Детали
        new_details = command.details if command.details is not None else task['details']
        
        # Время
        new_time_timestamp = task['time']
        display_time = datetime.fromtimestamp(task['time'], self.tz).strftime("%Y-%m-%d %H:%M")
        
        if command.time is not None:
            try:
                naive_dt = datetime.strptime(command.time, "%Y-%m-%d %H:%M")
                localized_dt = self.tz.localize(naive_dt)
                new_time_timestamp = int(localized_dt.timestamp())
                display_time = command.time
            except Exception:
                await message.answer(TaskMessages.invalid_update_time_format())
                return
        else:
            localized_dt = datetime.fromtimestamp(new_time_timestamp, self.tz)

        # Длительность
        new_duration = command.duration if command.duration is not None else (task['duration'] if 'duration' in task.keys() else None)

        # Важность
        new_importance = command.importance if command.importance is not None else (task['importance'] if 'importance' in task.keys() else None)

        # 3. Сохраняем изменения в БД
        await update_task(
            db=self.db,
            task_id=task_id,
            content=new_content,
            details=new_details,
            time_val=new_time_timestamp,
            duration=new_duration,
            importance=new_importance,
        )

        # 4. Обновляем планировщик
        self.scheduler_service.update_scheduler_jobs(
            task_id=task_id,
            content=new_content,
            details=new_details,
            localized_dt=localized_dt,
            duration=new_duration,
            importance=new_importance,
        )

        display_end_time = get_display_end_time(localized_dt, new_duration)

        confirm_text = TaskMessages.task_updated(
            content=new_content,
            display_time=display_time,
            details=new_details,
            duration=new_duration,
            display_end_time=display_end_time,
            importance=new_importance,
        )
        await message.answer(confirm_text, reply_markup=get_main_kb(), parse_mode="HTML")


    async def select(self, command: TaskActionSchema, message: Message):
        """
        Обрабатывает команду поиска задач (CRUD select).
        Кэширует найденные ID задач и показывает первую страницу результатов с пагинацией.
        """
        if not command.task_ids:
            await message.answer(TaskMessages.search_empty())
            return

        # Сохраняем результаты поиска для пагинации
        await save_user_search(
            db=self.db,
            user_id=self.user["id"],
            task_ids=command.task_ids,
            query=command.content or "поиск"
        )

        limit = 10
        total_count = len(command.task_ids)

        # Запрашиваем первую страницу найденных задач из БД
        tasks = await get_tasks_by_ids(
            db=self.db,
            task_ids=command.task_ids,
            user_id=self.user["id"],
            limit=limit,
            offset=0
        )

        if not tasks:
            await message.answer(TaskMessages.search_not_found())
            return

        response_text = TaskMessages.search_results(
            query=command.content or "поиск",
            tasks=tasks,
            tz=self.tz
        )

        if total_count > limit:
            lang = user_lang.get()
            page_word = "Page" if lang == "en" else "Страница"
            from_word = "of" if lang == "en" else "из"
            total_pages = (total_count + limit - 1) // limit
            response_text += f"\n\n📖 <i>{page_word} 1 {from_word} {total_pages}</i>"

        kb = get_pagination_keyboard(total_count, 1, limit, "page_select")

        await message.answer(response_text, parse_mode='HTML', reply_markup=kb or get_main_kb())


    async def delete(self, command: TaskActionSchema, message: Message):
        # Собираем все ID задач для выполнения/удаления
        task_ids = []
        if command.task_id:
            task_ids.append(command.task_id)
        if command.task_ids:
            for tid in command.task_ids:
                if tid not in task_ids:
                    task_ids.append(tid)

        if not task_ids:
            await message.answer(TaskMessages.task_delete_id_missing())
            return

        completed_titles = []
        not_found_count = 0
        denied_count = 0

        for tid in task_ids:
            # 1. Получаем задачу из базы данных
            task = await get_task_by_id(self.db, tid)
            if not task:
                not_found_count += 1
                continue

            # Проверяем права: принадлежит ли задача текущему пользователю
            if task['user_id'] != self.user['id']:
                denied_count += 1
                continue

            # 2. Помечаем задачу как выполненную (status = 1)
            await complete_task(self.db, tid)

            # 3. Удаляем из планировщика
            self.scheduler_service.remove_scheduler_jobs(tid)

            completed_titles.append(task['content'])

        if not completed_titles:
            if denied_count > 0:
                await message.answer(TaskMessages.task_delete_access_denied())
            elif not_found_count > 0:
                await message.answer(TaskMessages.task_not_found())
            return

        if len(completed_titles) == 1:
            confirm_text = TaskMessages.task_completed(completed_titles[0])
        else:
            confirm_text = TaskMessages.tasks_completed_plural(completed_titles)

        await message.answer(confirm_text, parse_mode='HTML', reply_markup=get_main_kb())

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