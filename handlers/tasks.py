from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import re
from datetime import datetime
from aiosqlite import Connection, Row

from inline_keyboards import get_task_keyboard
from database.crud.task import create_task, get_user_tasks, get_next_task, get_user_completed_tasks
from utils.formatters import format_tasks_message

router = Router()


@router.message(F.text == "Мои задачи")
async def get_my_tasks_handler(
        message: Message,
        db: Connection,
        user: Row
):
    tasks = await get_user_tasks(db, user["id"])

    response_text = format_tasks_message(
        tasks=tasks,
        empty_text="У вас пока нет запланированных задач. Используйте /create_task",
        header_text="Ваш список задач"
    )

    # 4. Отправляем пользователю
    await message.answer(response_text, parse_mode='Markdown')


@router.message(F.text == "Мои выполненные задачи")
async def get_my_completed_tasks_handler(
        message: Message,
        db: Connection,
        user: Row
):
    tasks = await get_user_completed_tasks(db, user["id"])


    response_text = format_tasks_message(
        tasks=tasks,
        empty_text="У вас пока нет выполненных задач. Используйте /create_task",
        header_text="Ваш список выполненных задач:"
    )

    # 4. Отправляем пользователю
    await message.answer(response_text, parse_mode='Markdown')
