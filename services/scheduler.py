from datetime import datetime, timedelta
import aiosqlite
import logging

from messages import TaskMessages
from utils.context import user_lang

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from keyboards.inline_keyboards import get_task_action_keyboard
from config import DB_PATH, TIMEZONE

from services.notion.service import update_task_status_in_notion

# Создаем глобальный инстанс планировщика
scheduler = AsyncIOScheduler(timezone=TIMEZONE)


async def send_task_notification(bot: Bot, user_id: int, task_text: str, task_id: int, task_details: str = None, task_importance: str = None):
    try:
        lang = "ru"
        notion_token = notion_db_id = notion_page_id = None
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    """
                    SELECT users.lang, users.notion_token, users.notion_db_id, tasks.notion_page_id
                    FROM users
                    JOIN tasks ON tasks.user_id = users.id
                    WHERE users.tg_id = ? AND tasks.id = ?
                    """,
                    (user_id, task_id)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        lang = row["lang"]
                        notion_token = row["notion_token"]
                        notion_db_id = row["notion_db_id"]
                        notion_page_id = row["notion_page_id"]
        except Exception as db_err:
            logging.error(f"Ошибка получения языка из БД для {user_id}: {db_err}")

        token = user_lang.set(lang)
        try:
            text = TaskMessages.task_notification(task_text, task_details, task_importance)
        finally:
            user_lang.reset(token)

        await bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode="HTML",
            reply_markup=get_task_action_keyboard(task_id)
        )

        if notion_page_id and notion_token and notion_db_id:
            await update_task_status_in_notion(
                notion_token=notion_token,
                notion_db_id=notion_db_id,
                page_id=notion_page_id,
                target_group="in_progress",
            )
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление юзеру {user_id}: {e}")


async def init_scheduler(bot: Bot):
    """Полная сборка планировщика: подключаемся к БД, забиваем задачи в очередь и стартуем"""
    tz = TIMEZONE

    # 1. Открываем короткое соединение с БД только ради вычитки активных задач
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Запрашиваем только невыполненные задачи с Telegram ID пользователя
        async with db.execute(
            """
            SELECT tasks.id, users.tg_id, tasks.content, tasks.details, tasks.time, tasks.duration, tasks.importance 
            FROM tasks 
            JOIN users ON tasks.user_id = users.id 
            WHERE tasks.status = 0
            """
        ) as cursor:
            pending_tasks = await cursor.fetchall()

    # 2. Проходимся по задачам и добавляем их в APScheduler
    now = datetime.now(tz)

    for task in pending_tasks:
        try:
            # Парсим UNIX timestamp из БД
            task_time = datetime.fromtimestamp(int(task['time']), tz=tz)
            task_dur = task['duration'] if 'duration' in task.keys() and task['duration'] else 0
            task_imp = task['importance'] if 'importance' in task.keys() else None

            # 1. Напоминание о начале задачи
            if task_time > now:
                scheduler.add_job(
                    send_task_notification,
                    trigger='date',
                    run_date=task_time,
                    kwargs={
                        'bot': bot,
                        'user_id': task['tg_id'],  # Передаем tg_id
                        'task_text': task['content'],
                        'task_details': task['details'],  # Передаем details
                        'task_id': task['id'],  # <-- Передаем ID задачи
                        'task_importance': task_imp,
                    },
                    id=f"task_{task['id']}",
                    replace_existing=True,
                    misfire_grace_time=3600
                )
        except Exception as e:
            logging.error(f"Ошибка при загрузке задачи ID {task.get('id')} в планировщик: {e}")

    # 3. Запускаем тиканье планировщика
    scheduler.start()
    logging.info("APScheduler успешно запущен и наполнен задачами из БД.")