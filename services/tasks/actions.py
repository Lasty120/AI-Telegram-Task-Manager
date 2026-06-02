from datetime import datetime, timedelta
import pytz
from aiogram import Bot
from aiogram.types import Message
from aiosqlite import Connection, Row

from messages import TaskMessages

from database.schemas import TaskActionSchema
from database.crud.task import create_task, get_task_by_id, get_tasks_by_ids, update_task, complete_task
from reply_keyboards import get_main_kb
from services.scheduler import scheduler, send_task_notification


class TaskActionsService:
    def __init__(self, db: Connection, user: Row, bot: Bot):
        self.db = db
        self.user = user
        self.bot = bot
        self.tz = pytz.timezone('Asia/Almaty')

    async def create(self, command: TaskActionSchema, message: Message):
        if not command.time:
            # Гибридный подход: если ИИ не вернул время, ставим дефолт на сегодня.
            # Например, на 18:00, а если уже вечер, то на +2 часа от текущего времени.
            now = datetime.now(self.tz)
            localized_dt = now + timedelta(hours=2)
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
        )

        # 2. Добавляем в планировщик на лету
        scheduler.add_job(
            send_task_notification,
            trigger='date',
            run_date=localized_dt,  # Объект datetime
            kwargs={
                'bot': self.bot,
                'user_id': self.user['tg_id'],  # Передаем Telegram ID для отправки уведомления
                'task_text': command.content,
                'task_details': command.details,
                'task_id': new_task_id
            },
            id=f"task_{new_task_id}",
            replace_existing=True
        )

        confirm_text = TaskMessages.task_created(
            content=command.content,
            display_time=display_time,
            details=command.details
        )
        await message.answer(confirm_text, reply_markup=get_main_kb())

    async def update(self, command: TaskActionSchema, message: Message):
        if not command.task_id:
            await message.answer(TaskMessages.TASK_UPDATE_ID_MISSING)
            return

        # 1. Получаем задачу из базы данных
        task = await get_task_by_id(self.db, command.task_id)
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

        # 3. Сохраняем изменения в БД
        await update_task(
            db=self.db,
            task_id=command.task_id,
            content=new_content,
            details=new_details,
            time_val=new_time_timestamp
        )

        # 4. Обновляем планировщик
        # Проверяем, в будущем ли время
        now = datetime.now(self.tz)
        if localized_dt > now:
            scheduler.add_job(
                send_task_notification,
                trigger='date',
                run_date=localized_dt,
                kwargs={
                    'bot': self.bot,
                    'user_id': self.user['tg_id'],
                    'task_text': new_content,
                    'task_details': new_details,
                    'task_id': command.task_id
                },
                id=f"task_{command.task_id}",
                replace_existing=True
            )
        else:
            # Если новое время ушло в прошлое, удаляем задачу из планировщика (если она была запланирована)
            try:
                scheduler.remove_job(f"task_{command.task_id}")
            except Exception:
                pass

        confirm_text = TaskMessages.task_updated(
            content=new_content,
            display_time=display_time,
            details=new_details
        )
        await message.answer(confirm_text, reply_markup=get_main_kb())


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
        await message.answer(response_text, parse_mode='Markdown', reply_markup=get_main_kb())


    async def delete(self, command: TaskActionSchema, message: Message):
        if not command.task_id:
            await message.answer(TaskMessages.TASK_DELETE_ID_MISSING)
            return

        # 1. Получаем задачу из базы данных
        task = await get_task_by_id(self.db, command.task_id)
        if not task:
            await message.answer(TaskMessages.TASK_NOT_FOUND)
            return

        # Проверяем права: принадлежит ли задача текущему пользователю
        if task['user_id'] != self.user['id']:
            await message.answer(TaskMessages.TASK_DELETE_ACCESS_DENIED)
            return

        # 2. Помечаем задачу как выполненную (status = 1)
        await complete_task(self.db, command.task_id)

        # 3. Удаляем из планировщика
        try:
            scheduler.remove_job(f"task_{command.task_id}")
        except Exception:
            pass

        confirm_text = TaskMessages.task_completed(task['content'])
        await message.answer(confirm_text, parse_mode='Markdown', reply_markup=get_main_kb())