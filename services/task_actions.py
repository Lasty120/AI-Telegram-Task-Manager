from datetime import datetime, timedelta
import pytz
from aiogram import Bot
from aiogram.types import Message, ReplyKeyboardMarkup
from aiosqlite import Connection, Row

from database.schemas import TaskActionSchema
from database.crud.task import create_task
from reply_keyboards import get_main_kb
from services.scheduler import scheduler, send_task_notification


async def handle_create_task(
        command: TaskActionSchema,
        message: Message,
        db: Connection,
        user: Row
):
    tz = pytz.timezone('Asia/Almaty')

    if not command.time:
        # Гибридный подход: если ИИ не вернул время, ставим дефолт на сегодня.
        # Например, на 18:00, а если уже вечер, то на +2 часа от текущего времени.
        now = datetime.now(tz)
        localized_dt = now + timedelta(hours=2)
        task_timestamp = int(localized_dt.timestamp())
        display_time = localized_dt.strftime("%Y-%m-%d %H:%M")
    else:
        # Парсим время, присланное ИИ
        try:
            naive_dt = datetime.strptime(command.time, "%Y-%m-%d %H:%M")
            localized_dt = tz.localize(naive_dt)
            task_timestamp = int(localized_dt.timestamp())
            display_time = command.time
        except Exception:
            await message.answer("⚠️ Некорректный формат времени от ИИ")
            return

    # 1. Сохраняем в БД и получаем ID новой задачи
    new_task_id = await create_task(
        db=db,
        user_id=user['id'],  # Обращение как к Row (по ключу)
        time=task_timestamp,
        content=command.content,
        details=command.details,
    )

    # 2. Добавляем в планировщик на лету
    bot: Bot = message.bot
    scheduler.add_job(
        send_task_notification,
        trigger='date',
        run_date=localized_dt,  # Объект datetime
        kwargs={
            'bot': bot,
            'user_id': user['tg_id'],  # Передаем Telegram ID для отправки уведомления
            'task_text': command.content,
            'task_details': command.details,
            'task_id': new_task_id
        },
        id=f"task_{new_task_id}",
        replace_existing=True
    )

    confirm_text = f"✅ Создана задача: {command.content} на {display_time}"
    if command.details:
        confirm_text += f"\n📖 Детали: {command.details}"
    await message.answer(confirm_text, reply_markup=get_main_kb())