from datetime import datetime
import aiosqlite

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
import logging

# Создаем глобальный инстанс планировщика
scheduler = AsyncIOScheduler(timezone="Asia/Almaty") # Укажи свой часовой пояс

async def send_task_notification(bot: Bot, user_id: int, task_text: str):
    """Эта функция будет вызываться планировщиком в назначенное время"""
    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"🔔 <b>Напоминание:</b>\n{task_text}",
            parse_mode="HTML"
        )
        # В идеале тут еще нужно сделать апдейт БД: перевести статус таски в "COMPLETED"
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление юзеру {user_id}: {e}")


async def init_scheduler(bot: Bot, db_path: str):
    """Полная сборка планировщика: подключаемся к БД, забиваем задачи в очередь и стартуем"""

    # 1. Открываем короткое соединение с БД только ради вычитки активных задач
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row

        # Запрашиваем только невыполненные задачи
        # Убедись, что имена колонок (is_completed, time) совпадают с твоей БД
        async with db.execute(
                "SELECT id, user_id, content, time FROM tasks WHERE is_completed = 0"
        ) as cursor:
            pending_tasks = await cursor.fetchall()

    # 2. Проходимся по задачам и добавляем их в APScheduler
    now = datetime.now()

    for task in pending_tasks:
        try:
            # Парсим время из строки (если в БД оно хранится как TEXT, например "2026-06-16 15:00")
            # Если у тебя в БД хранится timestamp (int), то используй datetime.fromtimestamp(task['time'])
            task_time = datetime.strptime(task['time'], "%Y-%m-%d %H:%M")

            # Планируем только те задачи, время которых еще не ушло
            if task_time > now:
                scheduler.add_job(
                    send_task_notification,
                    trigger='date',
                    run_date=task_time,
                    kwargs={
                        'bot': bot,
                        'user_id': task['user_id'],
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


# async def check_notifications(bot: Bot, db_path: str):
#     """
#     Фоновый процесс, который проверяет базу данных каждую минуту.
#     """
#     while True:
#         # Открываем соединение специально для фонового воркера
#         async with aiosqlite.connect(db_path) as db:
#             db.row_factory = aiosqlite.Row
#
#             # Получаем все задачи, время которых наступило
#             due_tasks = await get_due_tasks(db)
#
#             for task in due_tasks:
#                 try:
#                     # Отправляем сообщение пользователю
#                     await bot.send_message(
#                         chat_id=task['tg_id'],
#                         text=f"🔔 *Напоминание!*\n\n{task['content']}",
#                         parse_mode='Markdown'
#                     )
#                 except TelegramAPIError as e:
#                     # Юзер мог заблокировать бота, логируем ошибку, чтобы бот не упал
#                     print(f"Не удалось отправить сообщение {task['tg_id']}: {e}")
#                 finally:
#                     # Помечаем поле как completed
#                     await complete_task(db, task['id'])
#
#         # Засыпаем на 1 минуту (60 секунд) перед следующей проверкой
#         await asyncio.sleep(60)