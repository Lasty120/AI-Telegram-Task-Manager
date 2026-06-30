from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from messages import StartMessages
from keyboards.reply_keyboards import get_main_kb


router = Router()


@router.message(CommandStart())
async def cmd_start_handler(message: Message, user: dict):
    """
    Хэндлер на команду /start.
    Приветствует пользователя и выдаёт инструкцию по использованию бота.
    user: dict — пользователь, гарантированно созданный в UserMiddleware.
    """
    await message.answer(
        text=StartMessages.welcome(),
        parse_mode="HTML",
        reply_markup=get_main_kb()
    )