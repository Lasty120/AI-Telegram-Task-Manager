from services.scheduler import scheduler, send_task_notification
from aiogram import Bot
from aiogram.types import Message
from database.schemas import TaskActionSchema

from datetime import datetime
import pytz

from database.crud.task import create_task

from aiosqlite import Connection, Row

async def handle_create_task(
        command: TaskActionSchema,
        message: Message,
        db: Connection,
        user: Row
):
    if not command.time:
        await message.answer("⚠️ Пожалуйста, укажите время для напоминания.")
        return

    try:
        # 1. Парсим и переводим в UNIX-время для БД
        tz = pytz.timezone('Asia/Almaty')
        naive_dt = datetime.strptime(command.time, "%Y-%m-%d %H:%M")
        localized_dt = tz.localize(naive_dt)
        task_timestamp = int(localized_dt.timestamp())
    except Exception as e:
        await message.answer("⚠️ Некорректный формат времени. Пожалуйста, используйте YYYY-MM-DD HH:MM.")
        return

    # 2. Сохраняем в БД (записываем timestamp) и получаем ID
    new_task_id = await create_task(
        db=db,
        user_id=user['id'], # обращение по ключу
        time=str(task_timestamp), # записываем timestamp как строку/число
        content=command.content,
    )

    # 3. Добавляем в планировщик. run_date принимает localized_dt напрямую
    bot: Bot = message.bot
    scheduler.add_job(
        send_task_notification,
        trigger='date',
        run_date=localized_dt, # Передаем timezone-aware datetime объект
        kwargs={
            'bot': bot,
            'user_id': user['tg_id'], # Передаем Telegram ID, а не внутренний ID БД!
            'task_text': command.content
        },
        id=f"task_{new_task_id}",
        replace_existing=True
    )

    await message.answer(f"✅ Создана задача: {command.content} на {command.time}")