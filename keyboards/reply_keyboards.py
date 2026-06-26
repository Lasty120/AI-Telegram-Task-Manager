from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from utils.context import user_lang


def get_main_kb(opt_lang: str = None) -> ReplyKeyboardMarkup:
    """
    Главная reply-клавиатура с кнопками навигации.

    Кнопки:
    - «Мои задачи» / «My tasks»
    - «Мои выполненные задачи» / «My completed tasks»
    - «Задачи на сегодня» / «Tasks for today»
    - «Просроченные задачи» / «Overdue tasks»  ← новая кнопка

    Args:
        opt_lang: Если передан явно — использует этот язык (при смене языка).
                  Иначе берёт текущий из контекста.

    Returns:
        ReplyKeyboardMarkup с кнопками 2-1-1.
    """
    builder = ReplyKeyboardBuilder()
    lang = user_lang.get()

    translations = {
        "ru": {
            "my_tasks":   "Мои задачи",
            "completed":  "Мои выполненные задачи",
            "today_tasks": "Задачи на сегодня",
            "due_tasks":   "Просроченные задачи",
        },
        "en": {
            "my_tasks":   "My tasks",
            "completed":  "My completed tasks",
            "today_tasks": "Tasks for today",
            "due_tasks":   "Overdue tasks",
        },
    }

    # При смене языка через /change_language передаётся opt_lang
    if opt_lang:
        t = translations.get(opt_lang, translations["ru"])
    else:
        t = translations.get(lang, translations["ru"])

    builder.button(text=t["my_tasks"])
    builder.button(text=t["completed"])
    builder.button(text=t["today_tasks"])
    builder.button(text=t["due_tasks"])

    # Раскладка: первые две кнопки в ряд, потом по одной
    builder.adjust(2, 1, 1)

    return builder.as_markup(resize_keyboard=True)




def get_registration_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    lang = user_lang.get()

    translations = {
        "ru": {"skip": "Пропустить", "cancel": "Отмена"},
        "en": {"skip": "Skip",       "cancel": "Cancel"},
    }
    t = translations.get(lang, translations["ru"])

    builder.button(text=t["skip"])
    builder.button(text=t["cancel"])
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def get_cancel_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    lang = user_lang.get()

    translations = {
        "ru": {"cancel": "Отмена"},
        "en": {"cancel": "Cancel"},
    }
    t = translations.get(lang, translations["ru"])

    builder.button(text=t["cancel"])
    return builder.as_markup(resize_keyboard=True)