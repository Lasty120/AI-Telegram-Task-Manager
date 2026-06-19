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


def get_conflict_resolution_keyboard(old_task_id: int, new_task_id: int, old_task_content: str, new_task_content: str, add_to_notion: bool) -> InlineKeyboardMarkup:
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
    notion_flag = "1" if add_to_notion else "0"
    builder.button(text=t["move_old"], callback_data=f"resolve_conflict:move_old:{new_task_id}:{old_task_id}:{notion_flag}")
    builder.button(text=t["move_new"], callback_data=f"resolve_conflict:move_new:{new_task_id}:{old_task_id}:{notion_flag}")
    builder.button(text=t["ignore"], callback_data=f"resolve_conflict:ignore:{new_task_id}:{old_task_id}:{notion_flag}")
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


def get_status_selection_keyboard(options: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for idx, opt in enumerate(options):
        builder.button(text=opt, callback_data=f"select_status:{idx}")
    builder.adjust(1)
    return builder.as_markup()


def get_notion_users_keyboard(users: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for idx, u in enumerate(users):
        name = u["name"]
        if len(name) > 30:
            name = name[:27] + "..."
        builder.button(text=name, callback_data=f"select_notion_user:{idx}")
    builder.adjust(1)
    return builder.as_markup()


def get_admin_approval_keyboard(user_tg_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Одобрить ✅", callback_data=f"approve_notion:{user_tg_id}")
    builder.button(text="Отклонить ❌", callback_data=f"reject_notion:{user_tg_id}")
    builder.adjust(2)
    return builder.as_markup()



