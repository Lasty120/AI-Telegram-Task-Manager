from datetime import datetime, timedelta
import pytz
from aiogram import Bot
from aiogram.types import Message, ReplyKeyboardMarkup
from aiosqlite import Connection, Row

from database.schemas import TaskActionSchema
from database.crud.task import create_task, get_task_by_id, update_task
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


async def handle_update_task(
        command: TaskActionSchema,
        message: Message,
        db: Connection,
        user: Row
):
    if not command.task_id:
        await message.answer("⚠️ Не удалось определить, какую именно задачу нужно изменить.")
        return

    # 1. Получаем задачу из базы данных
    task = await get_task_by_id(db, command.task_id)
    if not task:
        await message.answer("⚠️ Задача с таким ID не найдена.")
        return

    # Проверяем права: принадлежит ли задача текущему пользователю
    if task['user_id'] != user['id']:
        await message.answer("⚠️ У вас нет прав на редактирование этой задачи.")
        return

    # 2. Определяем обновленные значения
    tz = pytz.timezone('Asia/Almaty')
    
    # Контент
    new_content = command.content if command.content is not None else task['content']
    
    # Детали
    new_details = command.details if command.details is not None else task['details']
    
    # Время
    new_time_timestamp = task['time']
    display_time = datetime.fromtimestamp(task['time'], tz).strftime("%Y-%m-%d %H:%M")
    
    if command.time is not None:
        try:
            naive_dt = datetime.strptime(command.time, "%Y-%m-%d %H:%M")
            localized_dt = tz.localize(naive_dt)
            new_time_timestamp = int(localized_dt.timestamp())
            display_time = command.time
        except Exception:
            await message.answer("⚠️ Некорректный формат времени от ИИ при обновлении.")
            return
    else:
        localized_dt = datetime.fromtimestamp(new_time_timestamp, tz)

    # 3. Сохраняем изменения в БД
    await update_task(
        db=db,
        task_id=command.task_id,
        content=new_content,
        details=new_details,
        time_val=new_time_timestamp
    )

    # 4. Обновляем планировщик
    bot: Bot = message.bot
    # Проверяем, в будущем ли время
    now = datetime.now(tz)
    if localized_dt > now:
        scheduler.add_job(
            send_task_notification,
            trigger='date',
            run_date=localized_dt,
            kwargs={
                'bot': bot,
                'user_id': user['tg_id'],
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

    confirm_text = f"🔄 Задача обновлена: {new_content} на {display_time}"
    if new_details:
        confirm_text += f"\n📖 Детали: {new_details}"
    await message.answer(confirm_text, reply_markup=get_main_kb())