# utils/pagination.py
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from keyboards.inline_keyboards import get_pagination_keyboard
from utils.context import user_lang


def get_paginated_text(base_text: str, current_page: int, total_count: int, limit: int) -> str:
    """
    Добавляет строку с информацией о текущей странице к базовому тексту.
    """
    if total_count <= limit:
        return base_text

    lang = user_lang.get()
    translations = {
        "ru": {
            "page_word": "Страница",
            "from_word": "из"
        },
        "en": {
            "page_word": "Page",
            "from_word": "of"
        }
    }
    lang_dict = translations.get(lang, translations["ru"])
    page_word = lang_dict["page_word"]
    from_word = lang_dict["from_word"]
    total_pages = (total_count + limit - 1) // limit

    return f"{base_text}\n\n📖 <i>{page_word} {current_page} {from_word} {total_pages}</i>"


async def send_paginated_message(
        message: Message, text: str, total_count: int, limit: int, prefix: str
):
    """
    Отправляет новое сообщение со списком и клавиатурой пагинации.
    """
    final_text = get_paginated_text(text, 1, total_count, limit)
    kb = get_pagination_keyboard(total_count, 1, limit, prefix)

    await message.answer(final_text, parse_mode='HTML', reply_markup=kb)


async def edit_paginated_message(
        callback: CallbackQuery, text: str, total_count: int, page: int, limit: int, prefix: str
):
    """
    Редактирует существующее сообщение при переключении страниц и подавляет
    ошибку отсутствия изменений (TelegramBadRequest).
    """
    final_text = get_paginated_text(text, page, total_count, limit)
    kb = get_pagination_keyboard(total_count, page, limit, prefix)

    await callback.answer()
    try:
        await callback.message.edit_text(final_text, parse_mode='HTML', reply_markup=kb)
    except TelegramBadRequest:
        # Подавляем исключение, если пользователь кликнул на активную страницу
        # и содержимое сообщения не изменилось
        pass