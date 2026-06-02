from aiogram.types import (
                           InlineKeyboardButton,
                           InlineKeyboardMarkup,
                           )
from aiogram.utils.keyboard import InlineKeyboardBuilder

MY_TASKS = InlineKeyboardButton(text="Мои задачи",callback_data="my_tasks")


def get_task_action_keyboard(task_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="Выполнить", callback_data=f"complete_task:{task_id}")
    builder.button(text="Отложить на 15 минут", callback_data=f"delay_task:{task_id}")
    builder.adjust(2)
    return builder.as_markup()


