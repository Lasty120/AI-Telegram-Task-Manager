from aiogram.types import (ReplyKeyboardMarkup,
                           KeyboardButton,
                           InlineKeyboardButton,
                           InlineKeyboardMarkup,
                           )
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def get_main_kb():
    builder = ReplyKeyboardBuilder()

    builder.button(text="Мои задачи")
    builder.button(text="Мои выполненные задачи")

    return builder.as_markup()