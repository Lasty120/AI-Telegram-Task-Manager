from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import re
from datetime import datetime
from aiosqlite import Connection, Row


from database.crud.task import create_task, get_user_tasks, get_user_completed_tasks
from utils.formatters import format_tasks_message
from messages import TaskMessages

router = Router()


@router.message(F.text.in_(["Мои задачи", "My tasks"]))
async def get_my_tasks_handler(
        message: Message,
        db: Connection,
        user: Row
):
    tasks = await get_user_tasks(db, user["id"])

    response_text = format_tasks_message(
        tasks=tasks,
        empty_text=TaskMessages.tasks_empty(),
        header_text=TaskMessages.tasks_header()
    )

    # 4. Отправляем пользователю
    await message.answer(response_text, parse_mode='HTML')


@router.message(F.text.in_(["Мои выполненные задачи", "My completed tasks"]))
async def get_my_completed_tasks_handler(
        message: Message,
        db: Connection,
        user: Row
):
    tasks = await get_user_completed_tasks(db, user["id"])


    response_text = format_tasks_message(
        tasks=tasks,
        empty_text=TaskMessages.completed_tasks_empty(),
        header_text=TaskMessages.completed_tasks_header()
    )

    # 4. Отправляем пользователю
    await message.answer(response_text, parse_mode='HTML')
