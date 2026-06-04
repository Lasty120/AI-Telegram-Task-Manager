from datetime import datetime
from aiogram import Bot
from aiogram.types import Message
from aiosqlite import Connection, Row

from messages import TaskMessages
from database.schemas import TaskActionSchema
from database.crud.task import create_task, get_task_by_id, get_tasks_by_ids, update_task, complete_task, get_user_tasks
from reply_keyboards import get_main_kb
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

    async def _find_first_free_slot(self, duration_mins: int) -> datetime:
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
                await message.answer(TaskMessages.INVALID_TIME_FORMAT)
                return

        # 1. Сохраняем в БД и получаем ID новой задачи
        new_task_id = await create_task(
            db=self.db,
            user_id=self.user['id'],  # Обращение как к Row (по ключу)
            time=task_timestamp,
            content=command.content,
            details=command.details,
            duration=command.duration,
        )

        # 2. Добавляем в планировщик на лету
        self.scheduler_service.update_scheduler_jobs(
            task_id=new_task_id,
            content=command.content,
            details=command.details,
            localized_dt=localized_dt,
            duration=command.duration
        )

        display_end_time = get_display_end_time(localized_dt, command.duration)

        confirm_text = TaskMessages.task_created(
            content=command.content,
            display_time=display_time,
            details=command.details,
            duration=command.duration,
            display_end_time=display_end_time
        )
        await message.answer(confirm_text, reply_markup=get_main_kb(), parse_mode="HTML")

    async def update(self, command: TaskActionSchema, message: Message):
        task_id = command.task_id or (command.task_ids[0] if command.task_ids else None)
        if not task_id:
            await message.answer(TaskMessages.TASK_UPDATE_ID_MISSING)
            return

        # 1. Получаем задачу из базы данных
        task = await get_task_by_id(self.db, task_id)
        if not task:
            await message.answer(TaskMessages.TASK_NOT_FOUND)
            return

        # Проверяем права: принадлежит ли задача текущему пользователю
        if task['user_id'] != self.user['id']:
            await message.answer(TaskMessages.TASK_UPDATE_ACCESS_DENIED)
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
                await message.answer(TaskMessages.INVALID_UPDATE_TIME_FORMAT)
                return
        else:
            localized_dt = datetime.fromtimestamp(new_time_timestamp, self.tz)

        # Длительность
        new_duration = command.duration if command.duration is not None else (task['duration'] if 'duration' in task.keys() else None)



        # 3. Сохраняем изменения в БД
        await update_task(
            db=self.db,
            task_id=task_id,
            content=new_content,
            details=new_details,
            time_val=new_time_timestamp,
            duration=new_duration,
        )

        # 4. Обновляем планировщик
        self.scheduler_service.update_scheduler_jobs(
            task_id=task_id,
            content=new_content,
            details=new_details,
            localized_dt=localized_dt,
            duration=new_duration
        )

        display_end_time = get_display_end_time(localized_dt, new_duration)

        confirm_text = TaskMessages.task_updated(
            content=new_content,
            display_time=display_time,
            details=new_details,
            duration=new_duration,
            display_end_time=display_end_time,
        )
        await message.answer(confirm_text, reply_markup=get_main_kb(), parse_mode="HTML")


    async def select(self, command: TaskActionSchema, message: Message):
        if not command.task_ids:
            await message.answer(TaskMessages.SEARCH_EMPTY)
            return

        # Запрашиваем найденные задачи из БД
        tasks = await get_tasks_by_ids(db=self.db, task_ids=command.task_ids, user_id=self.user["id"])

        if not tasks:
            await message.answer(TaskMessages.SEARCH_NOT_FOUND)
            return

        response_text = TaskMessages.search_results(
            query=command.content or "поиск",
            tasks=tasks,
            tz=self.tz
        )
        await message.answer(response_text, parse_mode='HTML', reply_markup=get_main_kb())


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
            await message.answer(TaskMessages.TASK_DELETE_ID_MISSING)
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
                await message.answer(TaskMessages.TASK_DELETE_ACCESS_DENIED)
            elif not_found_count > 0:
                await message.answer(TaskMessages.TASK_NOT_FOUND)
            return

        if len(completed_titles) == 1:
            confirm_text = TaskMessages.task_completed(completed_titles[0])
        else:
            tasks_list_str = ", ".join(f"\"{title}\"" for title in completed_titles)
            confirm_text = f"✅ Задачи выполнены: {tasks_list_str}"

        await message.answer(confirm_text, parse_mode='HTML', reply_markup=get_main_kb())