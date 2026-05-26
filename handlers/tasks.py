from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import re
from datetime import datetime
from aiosqlite import Connection, Row

from keyboards import get_task_keyboard
from messages.tasks import handle_message
from states import TaskStates
from database.crud.task import create_task, get_user_tasks, get_next_task

router = Router()


@router.callback_query(F.data == "my_tasks")
async def get_my_tasks_handler(
        callback: CallbackQuery,
        db: Connection,
        user: Row
):
    tasks = await get_user_tasks(db, user["id"])
    # 2. Если задач нет
    if not tasks:
        await callback.message.answer("У вас пока нет запланированных задач. Используйте /create_task")
        await callback.answer()  # Обязательно гасим "часики" на кнопке
        return

    # 3. Если задачи есть, красиво их форматируем
    response_lines = ["📋 *Ваш список задач:*", ""]

    for index, task in enumerate(tasks, 1):
        # Декодируем timestamp обратно в объект datetime
        task_datetime = datetime.fromtimestamp(task['time'])
        # Форматируем в строку, например "18:30" (или "%d.%m %H:%M" если важна дата)
        formatted_time = task_datetime.strftime('%H:%M')

        response_lines.append(f"{index}. *{task['content']}* — ⏰ {formatted_time}")

    response_text = "\n".join(response_lines)

    # 4. Отправляем пользователю
    await callback.message.edit_text(response_text, parse_mode='Markdown')

    # 5. Уведомляем Telegram, что инлайн-кнопка успешно обработана
    await callback.answer()


@router.message(Command('next_task'))
async def next_task_handler(
        message: Message,
        db: Connection,  # Прилетает из DbSessionMiddleware
        user: Row  # Прилетает из UserMiddleware
):
    # Получаем самую ближайшую задачу
    task = await get_next_task(db=db, user_id=user['id'])

    # Если задач на будущее не найдено
    if not task:
        await message.answer("У вас нет запланированных задач на будущее. Используйте /create_task")
        return

    # Переводим timestamp обратно в понятную дату/время
    task_datetime = datetime.fromtimestamp(task['time'])

    # Форматируем (если бот на один день, хватит '%H:%M',
    # но лучше добавить день и месяц '%d.%m в %H:%M' на случай переноса задачи на завтра)
    formatted_time = task_datetime.strftime('%d.%m в %H:%M')

    response_text = (
        f"⏰ *Ваша ближайшая задача:*\n\n"
        f"📝 {task['content']}\n"
        f"📅 Время: {formatted_time}"
    )

    await message.answer(response_text, parse_mode='Markdown')
