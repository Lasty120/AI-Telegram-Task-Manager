import asyncio
import logging
from aiogram import Bot, Dispatcher

from handlers import get_handlers_router
from config import TOKEN, DB_PATH
from middlewares.database import DbSessionMiddleware
from middlewares.user import UserMiddleware
from database.init_db import init_db
from services.scheduler import init_scheduler



async def main():
    dp = Dispatcher()
    bot = Bot(token=TOKEN)
    await init_db(db_path=DB_PATH)
    dp.include_router(get_handlers_router())

    await init_scheduler(bot)

    await bot.delete_webhook(drop_pending_updates=True)
    dp.update.middleware(DbSessionMiddleware(db_path=DB_PATH))
    dp.update.middleware(UserMiddleware())

    # Бесконечный цикл для автоматического переподключения
    while True:
        try:
            logging.info("Запуск поллинга...")
            await dp.start_polling(bot)
        except Exception as e:
            logging.error(f"Сетевая ошибка или сбой: {e}. Перезапуск через 5 секунд...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Bot has been started")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен пользователем")
    finally:
        # Корректно закрываем сессию только при полном выключении скрипта
        asyncio.run(bot.session.close())