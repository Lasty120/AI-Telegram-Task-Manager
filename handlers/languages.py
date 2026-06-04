from aiogram import Router, F
from  aiogram.filters import Command
from aiogram.types import Message

from aiosqlite import Row, Connection
from  database.crud.user import change_language
from messages import LangMessages

router = Router()

@router.message(Command("change_language"))
async def change_language_handler(
        message: Message,
        user: Row,
        db: Connection
):
    new_lang = await change_language(
        db=db,
        tg_id=message.from_user.id,
        user=user
    )
    await message.answer(
        text=LangMessages.lang_successfully_changed(new_lang=new_lang),
    )