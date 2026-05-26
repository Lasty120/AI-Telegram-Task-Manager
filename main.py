import asyncio
from aiogram import Bot, Dispatcher

from handlers import get_handlers_router
from config import TOKEN
from middlewares.database import DbSessionMiddleware
from middlewares.user import UserMiddleware
from database.init_db import init_db
from scheduler import check_notifications
dp = Dispatcher()
bot = Bot(token=TOKEN)

DB_PATH = "bot.db"

async def main():
    await init_db(db_path=DB_PATH)
    dp.include_router(get_handlers_router())


    await bot.delete_webhook(drop_pending_updates=True)
    dp.update.middleware(DbSessionMiddleware(db_path=DB_PATH))
    dp.update.middleware(UserMiddleware())

    asyncio.create_task(check_notifications(bot=bot, db_path=DB_PATH))
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    print("Bot has been started")
    asyncio.run(main())