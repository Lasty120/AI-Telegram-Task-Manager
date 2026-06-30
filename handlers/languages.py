import asyncpg
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database.repositories import UserRepository
from keyboards.reply_keyboards import get_main_kb
from messages import LangMessages


router = Router()


@router.message(Command("change_language"))
async def change_language_handler(
        message: Message,
        user: dict,
        db: asyncpg.Connection,
):
    """
    Хэндлер смены языка интерфейса.
    Создаёт UserRepository прямо в хендлере и вызывает update_lang().
    """
    user_repo = UserRepository(db)

    # Переключаем язык: ru → en, en → ru
    new_lang = "en" if user["lang"] == "ru" else "ru"
    await user_repo.update_lang(tg_id=message.from_user.id, lang=new_lang)

    await message.answer(
        text=LangMessages.lang_successfully_changed(new_lang=new_lang),
        reply_markup=get_main_kb(opt_lang=new_lang),
    )