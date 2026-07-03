"""
handlers/notifications.py

Хендлеры callback-кнопок уведомлений о задачах:
  - «Выполнить задачу» (complete_task)
  - «Отложить на 15 минут» (delay_task)
  - «Разрешить конфликт» (resolve_conflict)
"""

import logging
from datetime import datetime, timedelta

import asyncpg
from aiogram import Router, F
from aiogram.types import CallbackQuery
from apscheduler.jobstores.base import JobLookupError

from database.repositories import TaskRepository
from messages import TaskMessages, NotificationMessages
from services.notion.service import sync_task_status
from services.scheduler import scheduler, send_task_notification
from config import TIMEZONE
from services.tasks import ConflictService, SchedulerService, NotionSyncService

router = Router()


# ─────────────────────────────────────────────────────────────────────────────
# Выполнить задачу
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("complete_task:"))
async def complete_task_callback(callback: CallbackQuery, db: asyncpg.Connection, user: dict):
    """
    Отмечает задачу как выполненную по нажатию кнопки в уведомлении.
    Удаляет напоминание из планировщика и синхронизирует статус с Notion.
    """
    task_id = int(callback.data.split(":")[1])
    task_repo = TaskRepository(db)

    task = await task_repo.get_by_id(task_id)
    if not task:
        await callback.answer(TaskMessages.task_not_found(), show_alert=True)
        return

    if task["user_id"] != user["id"]:
        await callback.answer(TaskMessages.task_update_access_denied(), show_alert=True)
        return

    # Помечаем задачу выполненной через репозиторий
    await task_repo.complete(task_id)
    # Синхронизируем статус с Notion (если задача там есть)
    await sync_task_status(user, task, "complete")

    # Безопасно удаляем напоминание из планировщика
    try:
        scheduler.remove_job(f"task_{task_id}")
    except JobLookupError:
        pass

    await callback.answer(TaskMessages.task_completed_success())

    # Обновляем текст сообщения: убираем кнопки, добавляем отметку о выполнении
    text = TaskMessages.task_notification(task["content"], task["details"])
    text += NotificationMessages.task_successfully_completed()

    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Отложить задачу на 15 минут
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("delay_task:"))
async def delay_task_callback(callback: CallbackQuery, db: asyncpg.Connection, user: dict):
    """
    Откладывает задачу на 15 минут: обновляет время в БД и перепланирует напоминание.
    """
    task_id = int(callback.data.split(":")[1])
    task_repo = TaskRepository(db)

    task = await task_repo.get_by_id(task_id)
    if not task:
        await callback.answer(TaskMessages.task_not_found(), show_alert=True)
        return

    if task["user_id"] != user["id"]:
        await callback.answer(TaskMessages.task_update_access_denied(), show_alert=True)
        return

    now = datetime.now(TIMEZONE)
    new_time_dt = now + timedelta(minutes=15)
    new_time_timestamp = int(new_time_dt.timestamp())

    # Обновляем время задачи через репозиторий
    await task_repo.update(task_id, time=new_time_timestamp)

    # Перепланируем уведомление в APScheduler
    scheduler.add_job(
        send_task_notification,
        trigger="date",
        run_date=new_time_dt,
        kwargs={
            "bot": callback.message.bot,
            "user_id": user["tg_id"],
            "task_text": task["content"],
            "task_details": task["details"],
            "task_id": task_id,
        },
        id=f"task_{task_id}",
        replace_existing=True,
    )

    await callback.answer(NotificationMessages.task_delayed(new_time_dt), show_alert=True)

    # Обновляем сообщение в чате
    text = TaskMessages.task_notification(task["content"], task["details"])
    text += NotificationMessages.task_delayed(new_time_dt)

    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Разрешить конфликт времени задач
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("resolve_conflict:"))
async def resolve_conflict_callback(callback: CallbackQuery, db: asyncpg.Connection, user: dict):
    """
    Разрешает конфликт между двумя задачами на основе выбора пользователя.
    Создаёт все сервисы через TaskRepository (DI-паттерн).
    """
    parts = callback.data.split(":")
    if len(parts) < 5:
        await callback.answer(TaskMessages.invalid_request(), show_alert=True)
        return

    action = parts[1]
    new_task_id = int(parts[2])
    old_task_id = int(parts[3])
    add_to_notion = parts[4] == "1"

    # Создаём репозиторий и инициализируем все сервисы через него (DI-паттерн)
    task_repo = TaskRepository(db)
    scheduler_service = SchedulerService(bot=callback.message.bot, user=user)
    notion_service = NotionSyncService(task_repo=task_repo, user=user)
    conflict_service = ConflictService(
        task_repo=task_repo,
        user=user,
        scheduler_service=scheduler_service,
        notion_service=notion_service,
    )

    msg_text = await conflict_service.resolve_conflict(
        action=action,
        new_task_id=new_task_id,
        old_task_id=old_task_id,
        add_to_notion=add_to_notion,
    )

    await callback.answer()
    if msg_text:
        await callback.message.edit_text(
            text=msg_text,
            parse_mode="HTML",
            reply_markup=None,
        )
