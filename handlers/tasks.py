# tasks.py
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiosqlite import Connection, Row

from database.crud.task import (
    get_user_tasks,
    get_user_completed_tasks,
    get_user_tasks_count,
    get_user_completed_tasks_count,
    get_user_search,
    get_tasks_by_ids
)
from utils.formatters import format_tasks_message
from messages import TaskMessages
from config import TIMEZONE, TASKS_LIMIT_OF_PAGES as TASKS_LIMIT

# Импортируем новые утилиты
from utils.pagination import send_paginated_message, edit_paginated_message

router = Router()


@router.message(F.text.in_(["Мои задачи", "My tasks"]))
async def get_my_tasks_handler(message: Message, db: Connection, user: Row):
    total_count = await get_user_tasks_count(db, user["id"])
    tasks = await get_user_tasks(db, user["id"], limit=TASKS_LIMIT, offset=0)

    response_text = format_tasks_message(
        tasks=tasks,
        empty_text=TaskMessages.tasks_empty(),
    )

    await send_paginated_message(
        message=message, text=response_text, total_count=total_count,
        limit=TASKS_LIMIT, prefix="page_active"
    )


@router.callback_query(F.data.startswith("page_active:"))
async def page_active_callback(callback: CallbackQuery, db: Connection, user: Row):
    page = int(callback.data.split(":")[1])
    offset = (page - 1) * TASKS_LIMIT

    total_count = await get_user_tasks_count(db, user["id"])
    tasks = await get_user_tasks(db, user["id"], limit=TASKS_LIMIT, offset=offset)

    response_text = format_tasks_message(
        tasks=tasks,
        empty_text=TaskMessages.tasks_empty(),
    )

    await edit_paginated_message(
        callback=callback, text=response_text, total_count=total_count,
        page=page, limit=TASKS_LIMIT, prefix="page_active"
    )


@router.message(F.text.in_(["Мои выполненные задачи", "My completed tasks"]))
async def get_my_completed_tasks_handler(message: Message, db: Connection, user: Row):
    total_count = await get_user_completed_tasks_count(db, user["id"])
    tasks = await get_user_completed_tasks(db, user["id"], limit=TASKS_LIMIT, offset=0)

    response_text = format_tasks_message(
        tasks=tasks,
        empty_text=TaskMessages.completed_tasks_empty(),
    )

    await send_paginated_message(
        message=message, text=response_text, total_count=total_count,
        limit=TASKS_LIMIT, prefix="page_completed"
    )


@router.callback_query(F.data.startswith("page_completed:"))
async def page_completed_callback(callback: CallbackQuery, db: Connection, user: Row):
    page = int(callback.data.split(":")[1])
    offset = (page - 1) * TASKS_LIMIT

    total_count = await get_user_completed_tasks_count(db, user["id"])
    tasks = await get_user_completed_tasks(db, user["id"], limit=TASKS_LIMIT, offset=offset)

    response_text = format_tasks_message(
        tasks=tasks,
        empty_text=TaskMessages.completed_tasks_empty(),
    )

    await edit_paginated_message(
        callback=callback, text=response_text, total_count=total_count,
        page=page, limit=TASKS_LIMIT, prefix="page_completed"
    )


@router.callback_query(F.data.startswith("page_select:"))
async def page_select_callback(callback: CallbackQuery, db: Connection, user: Row):
    page = int(callback.data.split(":")[1])
    offset = (page - 1) * TASKS_LIMIT

    search_data = await get_user_search(db, user["id"])
    if not search_data:
        await callback.answer("Результаты поиска не найдены", show_alert=True)
        return

    task_ids, query = search_data
    total_count = len(task_ids)

    tasks = await get_tasks_by_ids(
        db=db, user_id=user["id"], task_ids=task_ids,
        limit=TASKS_LIMIT, offset=offset
    )

    response_text = TaskMessages.search_results(
        query=query, tasks=tasks, tz=TIMEZONE
    )

    await edit_paginated_message(
        callback=callback, text=response_text, total_count=total_count,
        page=page, limit=TASKS_LIMIT, prefix="page_select"
    )