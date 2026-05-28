from aiogram.types import (ReplyKeyboardMarkup,
                           KeyboardButton,
                           InlineKeyboardButton,
                           InlineKeyboardMarkup,
                           )
from aiogram.utils.keyboard import InlineKeyboardBuilder

MY_TASKS = InlineKeyboardButton(text="Мои задачи",callback_data="my_tasks")

def get_task_keyboard():
    builder = InlineKeyboardBuilder()

    builder.button(text="Перенести время",callback_data="move_time")
    builder.add(MY_TASKS)
    return builder.as_markup()

