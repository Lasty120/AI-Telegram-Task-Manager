from aiogram.types import (ReplyKeyboardMarkup,
                           KeyboardButton,
                           InlineKeyboardButton,
                           InlineKeyboardMarkup,
                           )
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from utils.context import user_lang

def get_main_kb(opt_lang: str = None):
        builder = ReplyKeyboardBuilder()
        lang = user_lang.get()

        translations = {
            "ru": {
                "my_tasks": "Мои задачи",
                "completed": "Мои выполненные задачи"
            },
            "en": {
                "my_tasks": "My tasks",
                "completed": "My completed tasks"
            }
        }
        # Логика для обработки смены  клавиатуры при смене языка
        if opt_lang:
            t = translations.get(opt_lang, translations["ru"])
        else:
            # Получаем словарь для текущего языка (по умолчанию 'ru')
            t = translations.get(lang, translations["ru"])

        builder.button(text=t["my_tasks"])
        builder.button(text=t["completed"])

        return builder.as_markup(resize_keyboard=True)


def get_registration_kb():
    builder = ReplyKeyboardBuilder()
    lang = user_lang.get()

    translations = {
        "ru": {
            "skip": "Пропустить",
            "cancel": "Отмена"
        },
        "en": {
            "skip": "Skip",
            "cancel": "Cancel"
        }
    }
    t = translations.get(lang, translations["ru"])

    builder.button(text=t["skip"])
    builder.button(text=t["cancel"])
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)