from datetime import datetime
import aiosqlite
import pytz
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

# Создаем глобальный инстанс планировщика
scheduler = AsyncIOScheduler(timezone="Asia/Almaty")


async def send_task_notification(bot: Bot, user_id: int, task_text: str):
    """Эта функция будет вызываться планировщиком в назначенное время"""
    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"🔔 <b>Напоминание:</b>\n{task_text}",
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление юзеру {user_id}: {e}")


async def init_scheduler(bot: Bot, db_path: str):
    """Полная сборка планировщика: подключаемся к БД, забиваем задачи в очередь и стартуем"""
    tz = pytz.timezone("Asia/Almaty")

    # 1. Открываем короткое соединение с БД только ради вычитки активных задач
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row

        # Запрашиваем только невыполненные задачи с Telegram ID пользователя
        async with db.execute(
            """
            SELECT tasks.id, users.tg_id, tasks.content, tasks.time 
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

            # Планируем только те задачи, время которых еще не ушло
            if task_time > now:
                scheduler.add_job(
                    send_task_notification,
                    trigger='date',
                    run_date=task_time,
                    kwargs={
                        'bot': bot,
                        'user_id': task['tg_id'],  # Передаем tg_id
                        'task_text': task['content']
                    },
                    id=f"task_{task['id']}",
                    replace_existing=True
                )
        except Exception as e:
            logging.error(f"Ошибка при загрузке задачи ID {task.get('id')} в планировщик: {e}")

    # 3. Запускаем тиканье планировщика
    scheduler.start()
    logging.info("APScheduler успешно запущен и наполнен задачами из БД.")