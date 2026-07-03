"""
handlers/due_tasks.py

Хендлер для кнопки «Просроченные задачи» в главной reply-клавиатуре.
Показывает все просроченные задачи пользователя и обрабатывает
инлайн-кнопки для массовых действий над ними.
"""

import asyncpg
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from config import TIMEZONE, TASKS_LIMIT_OF_PAGES as TASKS_LIMIT
from database.repositories import TaskRepository
from keyboards.due_tasks_kb import get_due_tasks_keyboard
from messages import DueTasksMessages, TaskMessages
from services.tasks.due_sync_service import DueSyncService
from utils.formatters import format_tasks_message
from utils.pagination import send_paginated_message

router = Router()


# ─────────────────────────────────────────────────────────────────────────────
# Reply-кнопка «Просроченные задачи» / «Overdue tasks»
# ─────────────────────────────────────────────────────────────────────────────

@router.message(F.text.in_(["Просроченные задачи", "Overdue tasks"]))
async def due_tasks_handler(message: Message, db: asyncpg.Connection, user: dict) -> None:
    """
    Показывает список всех активных просроченных задач пользователя.
    Прикрепляет инлайн-клавиатуру с действиями и подсказку о ручном выполнении.
    """
    task_repo = TaskRepository(db)
    service = DueSyncService(task_repo=task_repo, user=user)
    tasks = await service.get_due_tasks()

    if not tasks:
        await message.answer(
            text=DueTasksMessages.no_due_tasks(),
            parse_mode="HTML",
            reply_markup=get_due_tasks_keyboard(),
        )
        return

    # Формируем список задач через существующий форматтер
    tasks_text = format_tasks_message(
        tasks=tasks,
        empty_text=TaskMessages.tasks_empty(),
    )

    header = DueTasksMessages.due_tasks_header(count=len(tasks))
    full_text = f"{header}\n\n{tasks_text}"

    await message.answer(
        text=full_text,
        parse_mode="HTML",
        reply_markup=get_due_tasks_keyboard(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Callback: Выполнить все просроченные задачи
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "due_tasks:complete_all")
async def complete_all_due_callback(
    callback: CallbackQuery,
    db: asyncpg.Connection,
    user: dict,
) -> None:
    """
    Помечает все активные просроченные задачи пользователя как выполненные.
    Убирает инлайн-клавиатуру и показывает результат.
    """
    await callback.answer()

    task_repo = TaskRepository(db)
    service = DueSyncService(task_repo=task_repo, user=user)
    completed_count = await service.complete_all_due()

    if completed_count == 0:
        text = DueTasksMessages.complete_all_nothing()
    else:
        text = DueTasksMessages.complete_all_success(count=completed_count)

    # Редактируем оригинальное сообщение: убираем кнопки, показываем результат
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(text=text, parse_mode="HTML")


# ─────────────────────────────────────────────────────────────────────────────
# Callback: Синхронизировать выполненные из Notion
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "due_tasks:sync_notion")
async def sync_notion_callback(
    callback: CallbackQuery,
    db: asyncpg.Connection,
    user: dict,
) -> None:
    """
    Синхронизирует статусы задач с Notion:
    - Получает все активные задачи с notion_page_id.
    - Запрашивает Notion, у каких страниц статус начинается на «done».
    - Задачи с таким статусом помечаются выполненными локально.
    """
    await callback.answer()

    # Проверяем наличие Notion-интеграции
    notion_token = user.get("notion_token")
    notion_db_id = user.get("notion_db_id")

    if not notion_token or not notion_db_id:
        await callback.message.edit_text(
            text=DueTasksMessages.sync_notion_no_token(),
            parse_mode="HTML",
        )
        return

    # Показываем индикатор загрузки
    loading_msg = await callback.message.edit_text(
        text=DueTasksMessages.syncing_with_notion(),
        parse_mode="HTML",
    )

    task_repo = TaskRepository(db)
    service = DueSyncService(task_repo=task_repo, user=user)
    synced_count = await service.sync_completed_from_notion()

    await loading_msg.delete()
    await callback.message.answer(
        text=DueTasksMessages.sync_notion_success(count=synced_count),
        parse_mode="HTML",
    )
