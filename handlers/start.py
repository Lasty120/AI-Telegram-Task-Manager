from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiosqlite import Row

from reply_keyboards import get_main_kb


router = Router()

@router.message(CommandStart())
async def cmd_start_handler(message: Message, user: Row):
    """
    Хэндлер на команду /start.
    Приветствует пользователя и выдает инструкцию по использованию бота.
    """
    instructions = (
        "👋 <b>Добро пожаловать в умный менеджер задач!</b>\n\n"
        "Я помогу тебе планировать дела, запоминать слова и ничего не забывать. "
        "Тебе не нужно нажимать сложные кнопки — просто <b>напиши мне текст</b> или отправь <b>голосовое сообщение</b>, а я сам всё пойму и организую.\n\n"
        "🛠 <b>Что я умею:</b>\n\n"
        "📝 <b>Создавать задачи:</b>\n"
        "• <i>«Напомни позвонить маме завтра в 18:00»</i>\n"
        "• <i>«Учи слово Apple»</i>\n\n"
        "🔄 <b>Изменять планы:</b>\n"
        "• <i>«Перенеси созвон с Васей на 19:30»</i>\n\n"
        "✅ <b>Отмечать выполненное:</b>\n"
        "• <i>«Я купил хлеб, удали эту задачу»</i>\n\n"
        "🔍 <b>Искать планы:</b>\n"
        "• <i>«Какие у меня планы на выходные?»</i>\n\n"
        "👇 Используй кнопки в меню ниже, чтобы быстро просмотреть свои текущие или завершенные задачи."
    )

    await message.answer(
        text=instructions,
        parse_mode="HTML",
        reply_markup=get_main_kb()
    )