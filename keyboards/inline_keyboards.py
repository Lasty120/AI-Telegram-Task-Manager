from aiogram.types import (
                           InlineKeyboardButton,
                           InlineKeyboardMarkup,
                           )
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.context import user_lang
import math

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


def get_conflict_resolution_keyboard(old_task_id: int, new_task_id: int, old_task_content: str, new_task_content: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    lang = user_lang.get()


    # Сокращение названия задачи если она слишком длинная
    max_len = 20
    old_short = old_task_content[:max_len] + "..." if len(old_task_content) > max_len else old_task_content
    new_short = new_task_content[:max_len] + "..." if len(new_task_content) > max_len else new_task_content

    translations = {
        "ru": {
            "move_old": f"Перенести \"{old_short}\"",
            "move_new": f"Перенести \"{new_short}\"",
            "ignore": "Игнорировать конфликт"
        },
        "en": {
            "move_old": f"Move \"{old_short}\"",
            "move_new": f"Move \"{new_short}\"",
            "ignore": "Ignore the conflict"
        }
    }

    t = translations.get(lang, translations["ru"])
    builder.button(text=t["move_old"], callback_data=f"resolve_conflict:move_old:{new_task_id}:{old_task_id}")
    builder.button(text=t["move_new"], callback_data=f"resolve_conflict:move_new:{new_task_id}:{old_task_id}")
    builder.button(text=t["ignore"], callback_data=f"resolve_conflict:ignore")
    builder.adjust(1)
    return builder.as_markup()


def get_pagination_keyboard(total_count: int, current_page: int, limit: int, prefix: str) -> InlineKeyboardMarkup | None:
    """
    Создает инлайн-клавиатуру для постраничного перелистывания задач.
    Отображает номера страниц, при этом текущая страница выделена точками.
    """
    if total_count <= limit:
        return None

    total_pages = math.ceil(total_count / limit)
    builder = InlineKeyboardBuilder()

    for page in range(1, total_pages + 1):
        text = f"• {page} •" if page == current_page else str(page)
        builder.button(text=text, callback_data=f"{prefix}:{page}")

    builder.adjust(5)
    return builder.as_markup()



