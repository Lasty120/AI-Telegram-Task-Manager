import asyncio
import aiosqlite
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

# Импортируем наши новые CRUD функции
from database.crud.task import get_due_tasks, complete_task


async def check_notifications(bot: Bot, db_path: str):
    """
    Фоновый процесс, который проверяет базу данных каждую минуту.
    """
    while True:
        # Открываем соединение специально для фонового воркера
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            # Получаем все задачи, время которых наступило
            due_tasks = await get_due_tasks(db)

            for task in due_tasks:
                try:
                    # Отправляем сообщение пользователю
                    await bot.send_message(
                        chat_id=task['tg_id'],
                        text=f"🔔 *Напоминание!*\n\n{task['content']}",
                        parse_mode='Markdown'
                    )
                except TelegramAPIError as e:
                    # Юзер мог заблокировать бота, логируем ошибку, чтобы бот не упал
                    print(f"Не удалось отправить сообщение {task['tg_id']}: {e}")
                finally:
                    # Помечаем поле как completed
                    await complete_task(db, task['id'])

        # Засыпаем на 1 минуту (60 секунд) перед следующей проверкой
        await asyncio.sleep(60)