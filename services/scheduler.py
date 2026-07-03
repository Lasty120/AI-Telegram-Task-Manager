"""
services/scheduler.py

Глобальный планировщик APScheduler + функции фоновых уведомлений и рассылок.
Изменения (Этап 5):
  - aiosqlite полностью убран.
  - Для разовых фоновых задач (send_task_notification, send_daily_tasks_summary)
    используется пул asyncpg из database.pool.get_pool().
  - init_scheduler принимает пул явно и передаёт его в send_daily_tasks_summary.
  - Репозитории UserRepository и TaskRepository создаются внутри каждой фоновой функции.
"""

import asyncio
import logging
from datetime import datetime, timedelta

import asyncpg
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from keyboards.inline_keyboards import get_task_action_keyboard
from config import TIMEZONE, TASKS_LIMIT_OF_PAGES as TASKS_LIMIT
from database.repositories import UserRepository, TaskRepository
from database.pool import get_pool
from messages import TaskMessages
from utils.context import user_lang
from utils.date_utils import is_fallback_timestamp
from utils.formatters import format_tasks_message
from utils.pagination import send_paginated_message_to_chat


# Глобальный инстанс планировщика
scheduler = AsyncIOScheduler(timezone=TIMEZONE)


# ─────────────────────────────────────────────────────────────────────────────
# Уведомление о начале задачи
# ─────────────────────────────────────────────────────────────────────────────

async def send_task_notification(
    bot: Bot,
    user_id: int,
    task_text: str,
    task_id: int,
    task_details: str = None,
    task_importance: str = None,
):
    """
    Отправляет пользователю уведомление о наступлении времени задачи.
    Берёт соединение из глобального пула asyncpg для получения языка и Notion-данных.
    """
    try:
        lang = "ru"
        # Читаем язык пользователя и данные Notion из БД через пул
        pool = get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT u.lang, u.notion_token, u.notion_db_id,
                       u.notion_status_notified, t.notion_page_id
                FROM users u
                JOIN tasks t ON t.user_id = u.id
                WHERE u.tg_id = $1 AND t.id = $2
                """,
                user_id, task_id,
            )
            if row:
                lang = row["lang"] or "ru"

        token = user_lang.set(lang)
        try:
            text = TaskMessages.task_notification(task_text, task_details, task_importance)
        finally:
            user_lang.reset(token)

        await bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode="HTML",
            reply_markup=get_task_action_keyboard(task_id),
        )

    except Exception as e:
        logging.error(f"Не удалось отправить уведомление пользователю {user_id}: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Инициализация планировщика при старте бота
# ─────────────────────────────────────────────────────────────────────────────

async def init_scheduler(bot: Bot):
    """
    Полная сборка планировщика:
      1. Читает активные задачи из БД через asyncpg-пул.
      2. Добавляет напоминания в APScheduler.
      3. Регистрирует ежедневные рассылки задач.
      4. Запускает планировщик.
    """
    tz = TIMEZONE
    pool = get_pool()

    # 1. Загружаем все активные задачи из БД одним запросом
    async with pool.acquire() as conn:
        pending_tasks = await conn.fetch(
            """
            SELECT t.id, u.tg_id, t.content, t.details, t.time, t.duration, t.importance
            FROM tasks t
            JOIN users u ON t.user_id = u.id
            WHERE t.status = 0
            """,
        )

    # 2. Добавляем напоминания о задачах в APScheduler
    now = datetime.now(tz)
    for task in pending_tasks:
        try:
            # Пропускаем задачи без срока (метка 2060)
            if is_fallback_timestamp(int(task["time"])):
                continue

            task_time = datetime.fromtimestamp(int(task["time"]), tz=tz)
            task_imp = task["importance"]

            # Планируем напоминание только для будущих задач
            if task_time > now:
                scheduler.add_job(
                    send_task_notification,
                    trigger="date",
                    run_date=task_time,
                    kwargs={
                        "bot": bot,
                        "user_id": task["tg_id"],
                        "task_text": task["content"],
                        "task_details": task["details"],
                        "task_id": task["id"],
                        "task_importance": task_imp,
                    },
                    id=f"task_{task['id']}",
                    replace_existing=True,
                    misfire_grace_time=3600,
                )
        except Exception as e:
            logging.error(f"Ошибка при загрузке задачи ID {task.get('id')} в планировщик: {e}")

    # 3. Ежедневная рассылка в 9:00 и 21:00
    scheduler.add_job(
        send_daily_tasks_summary,
        trigger="cron",
        hour=9,
        minute=0,
        args=[bot],
        id="daily_tasks_morning",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        send_daily_tasks_summary,
        trigger="cron",
        hour=21,
        minute=0,
        args=[bot],
        id="daily_tasks_evening",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # 4. Запускаем планировщик
    scheduler.start()
    logging.info("APScheduler успешно запущен и наполнен задачами из БД.")


# ─────────────────────────────────────────────────────────────────────────────
# Ежедневная рассылка задач на сегодня
# ─────────────────────────────────────────────────────────────────────────────

async def send_daily_tasks_summary(bot: Bot):
    """
    Отправляет всем пользователям список задач на сегодня в 9:00 и 21:00.
    Использует пул asyncpg для получения всех пользователей и их задач.
    """
    logging.info("Запуск рассылки задач на сегодня...")

    now = datetime.now(TIMEZONE)
    start_ts = int(TIMEZONE.localize(datetime(now.year, now.month, now.day, 0, 0, 0)).timestamp())
    end_ts = int(TIMEZONE.localize(datetime(now.year, now.month, now.day, 23, 59, 59)).timestamp())

    pool = get_pool()

    try:
        async with pool.acquire() as conn:
            user_repo = UserRepository(conn)
            task_repo = TaskRepository(conn)

            users = await user_repo.get_all()

            for user in users:
                user_id = user["id"]
                tg_id = user["tg_id"]
                lang = user["lang"] or "ru"

                # Устанавливаем язык пользователя в контекстную переменную
                token = user_lang.set(lang)
                try:
                    total_count = await task_repo.get_today_count(
                        user_id=user_id, start_ts=start_ts, end_ts=end_ts
                    )
                    # Если задач нет — не отправляем пустое сообщение
                    if total_count == 0:
                        continue

                    tasks = await task_repo.get_today(
                        user_id=user_id,
                        start_ts=start_ts,
                        end_ts=end_ts,
                        limit=TASKS_LIMIT,
                        offset=0,
                    )

                    response_text = format_tasks_message(
                        tasks=tasks,
                        empty_text=TaskMessages.today_tasks_empty(),
                    )

                    await send_paginated_message_to_chat(
                        bot=bot,
                        chat_id=tg_id,
                        text=response_text,
                        total_count=total_count,
                        limit=TASKS_LIMIT,
                        prefix="page_today",
                    )

                except Exception as user_err:
                    logging.error(
                        f"Ошибка при отправке сводки задач пользователю {tg_id}: {user_err}"
                    )
                finally:
                    user_lang.reset(token)
                    # Небольшая пауза между отправками — защита от flood limit
                    await asyncio.sleep(0.05)

    except Exception as e:
        logging.error(f"Ошибка при выполнении рассылки задач: {e}")