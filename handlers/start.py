from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiosqlite import Row
from messages import StartMessages

from keyboards.reply_keyboards import get_main_kb


router = Router()

@router.message(CommandStart())
async def cmd_start_handler(message: Message, user: Row):
    """
    Хэндлер на команду /start.
    Приветствует пользователя и выдает инструкцию по использованию бота.
    """

    await message.answer(
        text=StartMessages.WELCOME,
        parse_mode="HTML",
        reply_markup=get_main_kb()
    )