"""
handlers/tasks_ai.py

Хендлер для обработки текстовых команд пользователя через ИИ.

"""

import asyncpg
from aiogram import F, Router
from aiogram.types import Message

from database.repositories import TaskRepository, SearchRepository
from services.tasks.processor import process_task_command

router = Router()


@router.message(F.text)
async def process_task_handler(
        message: Message,
        db: asyncpg.Connection,
        user: dict,
):
    """
    Обрабатывает произвольный текст пользователя как команду над задачами.
    Репозитории создаются здесь и передаются в процессор (DI-паттерн).
    """
    task_repo = TaskRepository(db)
    search_repo = SearchRepository(db)

    await process_task_command(
        text=message.text,
        message=message,
        user=user,
        task_repo=task_repo,
        search_repo=search_repo,
    )