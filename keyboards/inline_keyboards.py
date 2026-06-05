from aiogram.types import (
                           InlineKeyboardButton,
                           InlineKeyboardMarkup,
                           )
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.context import user_lang

MY_TASKS = InlineKeyboardButton(text="Мои задачи",callback_data="my_tasks")


def get_task_action_keyboard(task_id: int):
    builder = InlineKeyboardBuilder()
    lang = user_lang.get()

    translations = {
        "ru": {
            "complete": "Выполнить",
            "delay": "Отложить на 15 минут"
        },
        "en": {
            "complete": "Complete",
            "delay": "Delay 15 min"
        }
    }

    t = translations.get(lang, translations["ru"])

    builder.button(text=t["complete"], callback_data=f"complete_task:{task_id}")
    builder.button(text=t["delay"], callback_data=f"delay_task:{task_id}")

    builder.adjust(2)
    return builder.as_markup()


