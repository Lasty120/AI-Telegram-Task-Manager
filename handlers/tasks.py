"""
handlers/tasks.py

Хендлеры для работы со списками задач (активные, выполненные, на сегодня, поиск).
Изменения (Этап 5):
  - aiosqlite.Connection/Row убраны.
  - Вместо старых CRUD-функций используются TaskRepository и SearchRepository,
    которые инстанцируются прямо в хендлере из asyncpg.Connection.
"""

from datetime import datetime

import asyncpg
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery

from database.repositories import TaskRepository, SearchRepository
from utils.formatters import format_tasks_message
from messages import TaskMessages
from config import TIMEZONE, TASKS_LIMIT_OF_PAGES as TASKS_LIMIT
from utils.pagination import send_paginated_message, edit_paginated_message

router = Router()


# ─────────────────────────────────────────────────────────────────────────────
# Активные задачи
# ─────────────────────────────────────────────────────────────────────────────

@router.message(F.text.in_(["Мои задачи", "My tasks"]))
async def get_my_tasks_handler(message: Message, db: asyncpg.Connection, user: dict):
    """Показывает список активных задач пользователя с пагинацией."""
    task_repo = TaskRepository(db)

    total_count = await task_repo.get_active_count(user_id=user["id"])
    tasks = await task_repo.get_active(user_id=user["id"], limit=TASKS_LIMIT, offset=0)

    response_text = format_tasks_message(
        tasks=tasks,
        empty_text=TaskMessages.tasks_empty(),
    )

    await send_paginated_message(
        message=message, text=response_text, total_count=total_count,
        limit=TASKS_LIMIT, prefix="page_active",
    )


@router.callback_query(F.data.startswith("page_active:"))
async def page_active_callback(callback: CallbackQuery, db: asyncpg.Connection, user: dict):
    """Постраничная навигация по активным задачам."""
    task_repo = TaskRepository(db)

    page = int(callback.data.split(":")[1])
    offset = (page - 1) * TASKS_LIMIT

    total_count = await task_repo.get_active_count(user_id=user["id"])
    tasks = await task_repo.get_active(user_id=user["id"], limit=TASKS_LIMIT, offset=offset)

    response_text = format_tasks_message(
        tasks=tasks,
        empty_text=TaskMessages.tasks_empty(),
    )

    await edit_paginated_message(
        callback=callback, text=response_text, total_count=total_count,
        page=page, limit=TASKS_LIMIT, prefix="page_active",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Выполненные задачи
# ─────────────────────────────────────────────────────────────────────────────

@router.message(F.text.in_(["Мои выполненные задачи", "My completed tasks"]))
async def get_my_completed_tasks_handler(message: Message, db: asyncpg.Connection, user: dict):
    """Показывает список выполненных задач пользователя с пагинацией."""
    task_repo = TaskRepository(db)

    total_count = await task_repo.get_completed_count(user_id=user["id"])
    tasks = await task_repo.get_completed(user_id=user["id"], limit=TASKS_LIMIT, offset=0)

    response_text = format_tasks_message(
        tasks=tasks,
        empty_text=TaskMessages.completed_tasks_empty(),
    )

    await send_paginated_message(
        message=message, text=response_text, total_count=total_count,
        limit=TASKS_LIMIT, prefix="page_completed",
    )


@router.callback_query(F.data.startswith("page_completed:"))
async def page_completed_callback(callback: CallbackQuery, db: asyncpg.Connection, user: dict):
    """Постраничная навигация по выполненным задачам."""
    task_repo = TaskRepository(db)

    page = int(callback.data.split(":")[1])
    offset = (page - 1) * TASKS_LIMIT

    total_count = await task_repo.get_completed_count(user_id=user["id"])
    tasks = await task_repo.get_completed(user_id=user["id"], limit=TASKS_LIMIT, offset=offset)

    response_text = format_tasks_message(
        tasks=tasks,
        empty_text=TaskMessages.completed_tasks_empty(),
    )

    await edit_paginated_message(
        callback=callback, text=response_text, total_count=total_count,
        page=page, limit=TASKS_LIMIT, prefix="page_completed",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Результаты поиска (пагинация)
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("page_select:"))
async def page_select_callback(callback: CallbackQuery, db: asyncpg.Connection, user: dict):
    """
    Постраничная навигация по результатам поиска.
    Кэш поиска хранится в SearchRepository.
    """
    task_repo = TaskRepository(db)
    search_repo = SearchRepository(db)

    page = int(callback.data.split(":")[1])
    offset = (page - 1) * TASKS_LIMIT

    # Загружаем сохранённый поисковый запрос из репозитория
    search_data = await search_repo.get(user_id=user["id"])
    if not search_data:
        await callback.answer("Результаты поиска не найдены", show_alert=True)
        return

    task_ids = search_data["task_ids"]
    query = search_data["query"]
    total_count = len(task_ids)

    tasks = await task_repo.get_by_ids(
        user_id=user["id"], ids=task_ids,
        limit=TASKS_LIMIT, offset=offset,
    )

    response_text = TaskMessages.search_results(
        query=query, tasks=tasks, tz=TIMEZONE,
    )

    await edit_paginated_message(
        callback=callback, text=response_text, total_count=total_count,
        page=page, limit=TASKS_LIMIT, prefix="page_select",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Задачи на сегодня
# ─────────────────────────────────────────────────────────────────────────────

@router.message(F.text.in_(["Задачи на сегодня", "Tasks for today"]))
async def get_today_tasks_handler(message: Message, db: asyncpg.Connection, user: dict):
    """Показывает активные задачи пользователя на текущий день."""
    task_repo = TaskRepository(db)

    now = datetime.now(TIMEZONE)
    start_ts = int(TIMEZONE.localize(datetime(now.year, now.month, now.day, 0, 0, 0)).timestamp())
    end_ts = int(TIMEZONE.localize(datetime(now.year, now.month, now.day, 23, 59, 59)).timestamp())

    total_count = await task_repo.get_today_count(user_id=user["id"], start_ts=start_ts, end_ts=end_ts)
    tasks = await task_repo.get_today(
        user_id=user["id"], start_ts=start_ts, end_ts=end_ts,
        limit=TASKS_LIMIT, offset=0,
    )

    response_text = format_tasks_message(
        tasks=tasks,
        empty_text=TaskMessages.today_tasks_empty(),
    )

    await send_paginated_message(
        message=message, text=response_text, total_count=total_count,
        limit=TASKS_LIMIT, prefix="page_today",
    )


@router.callback_query(F.data.startswith("page_today:"))
async def page_today_callback(callback: CallbackQuery, db: asyncpg.Connection, user: dict):
    """Постраничная навигация по задачам на сегодня."""
    task_repo = TaskRepository(db)

    page = int(callback.data.split(":")[1])
    offset = (page - 1) * TASKS_LIMIT

    now = datetime.now(TIMEZONE)
    start_ts = int(TIMEZONE.localize(datetime(now.year, now.month, now.day, 0, 0, 0)).timestamp())
    end_ts = int(TIMEZONE.localize(datetime(now.year, now.month, now.day, 23, 59, 59)).timestamp())

    total_count = await task_repo.get_today_count(user_id=user["id"], start_ts=start_ts, end_ts=end_ts)
    tasks = await task_repo.get_today(
        user_id=user["id"], start_ts=start_ts, end_ts=end_ts,
        limit=TASKS_LIMIT, offset=offset,
    )

    response_text = format_tasks_message(
        tasks=tasks,
        empty_text=TaskMessages.today_tasks_empty(),
    )

    await edit_paginated_message(
        callback=callback, text=response_text, total_count=total_count,
        page=page, limit=TASKS_LIMIT, prefix="page_today",
    )