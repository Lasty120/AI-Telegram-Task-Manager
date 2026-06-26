"""
Дополнение к keyboards/inline_keyboards.py.
Содержит клавиатуру для управления просроченными задачами.
Добавить функции в конец существующего keyboards/inline_keyboards.py.
"""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.context import user_lang


def get_due_tasks_keyboard() -> InlineKeyboardMarkup:
    """
    Инлайн-клавиатура для сообщения с просроченными задачами.

    Кнопки:
    - «Выполнить все просроченные задачи» — помечает все как done локально.
    - «Синхронизировать с Notion» — проверяет, какие задачи уже done в Notion,
      и завершает их локально.

    Returns:
        InlineKeyboardMarkup с двумя кнопками.
    """
    builder = InlineKeyboardBuilder()
    lang = user_lang.get()

    translations = {
        "ru": {
            "complete_all": "Выполнить все просроченные задачи",
            "sync_notion":  "Синхронизировать выполненные из Notion",
        },
        "en": {
            "complete_all": "Complete all overdue tasks",
            "sync_notion":  "Sync completed tasks from Notion",
        },
    }

    t = translations.get(lang, translations["ru"])

    builder.button(text=t["complete_all"], callback_data="due_tasks:complete_all")
    builder.button(text=t["sync_notion"],  callback_data="due_tasks:sync_notion")
    builder.adjust(1)

    return builder.as_markup()
