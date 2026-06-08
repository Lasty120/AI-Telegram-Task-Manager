from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiosqlite import Connection, Row

from database.crud.task import (
    get_user_tasks,
    get_user_completed_tasks,
    get_user_tasks_count,
    get_user_completed_tasks_count,
    get_user_search,
    get_tasks_by_ids
)
from utils.formatters import format_tasks_message
from messages import TaskMessages
from keyboards.inline_keyboards import get_pagination_keyboard
from utils.context import user_lang
from config import TIMEZONE

router = Router()


async def answer_with_pages_kb(limit: int, message: Message, response_text: str, total_count: int):
    """
    Отвечает с клавиатурой страниц
    """
    if total_count > limit:
        lang = user_lang.get()
        page_word = "Page" if lang == "en" else "Страница"
        from_word = "of" if lang == "en" else "из"
        total_pages = (total_count + limit - 1) // limit
        response_text += f"\n\n📖 <i>{page_word} 1 {from_word} {total_pages}</i>"

    kb = get_pagination_keyboard(total_count, 1, limit, "page_completed")

    await message.answer(response_text, parse_mode='HTML', reply_markup=kb)


@router.message(F.text.in_(["Мои задачи", "My tasks"]))
async def get_my_tasks_handler(
        message: Message,
        db: Connection,
        user: Row
):
    """
    Хэндлер для отображения первой страницы списка активных задач.
    Отображает до 10 задач и добавляет клавиатуру пагинации при необходимости.
    """
    limit = 10
    total_count = await get_user_tasks_count(db, user["id"])
    tasks = await get_user_tasks(db, user["id"], limit=limit, offset=0)

    response_text = format_tasks_message(
        tasks=tasks,
        empty_text=TaskMessages.tasks_empty(),
        header_text=TaskMessages.tasks_header()
    )

    await answer_with_pages_kb(limit, message, response_text, total_count)


@router.callback_query(F.data.startswith("page_active:"))
async def page_active_callback(callback: CallbackQuery, db: Connection, user: Row):
    """
    Коллбэк-хэндлер для переключения страниц активных задач.
    """
    page = int(callback.data.split(":")[1])
    limit = 10
    offset = (page - 1) * limit

    total_count = await get_user_tasks_count(db, user["id"])
    tasks = await get_user_tasks(db, user["id"], limit=limit, offset=offset)

    response_text = format_tasks_message(
        tasks=tasks,
        empty_text=TaskMessages.tasks_empty(),
        header_text=TaskMessages.tasks_header()
    )

    lang = user_lang.get()
    page_word = "Page" if lang == "en" else "Страница"
    from_word = "of" if lang == "en" else "из"
    total_pages = (total_count + limit - 1) // limit
    response_text += f"\n\n📖 <i>{page_word} {page} {from_word} {total_pages}</i>"

    kb = get_pagination_keyboard(total_count, page, limit, "page_active")

    await callback.message.edit_text(response_text, parse_mode='HTML', reply_markup=kb)
    await callback.answer()


@router.message(F.text.in_(["Мои выполненные задачи", "My completed tasks"]))
async def get_my_completed_tasks_handler(
        message: Message,
        db: Connection,
        user: Row
):
    """
    Хэндлер для отображения первой страницы списка выполненных задач.
    Отображает до 10 задач и добавляет клавиатуру пагинации при необходимости.
    """
    limit = 10
    total_count = await get_user_completed_tasks_count(db, user["id"])
    tasks = await get_user_completed_tasks(db, user["id"], limit=limit, offset=0)

    response_text = format_tasks_message(
        tasks=tasks,
        empty_text=TaskMessages.completed_tasks_empty(),
        header_text=TaskMessages.completed_tasks_header()
    )

    await answer_with_pages_kb(limit, message, response_text, total_count)



@router.callback_query(F.data.startswith("page_completed:"))
async def page_completed_callback(callback: CallbackQuery, db: Connection, user: Row):
    """
    Коллбэк-хэндлер для переключения страниц выполненных задач.
    """
    page = int(callback.data.split(":")[1])
    limit = 10
    offset = (page - 1) * limit

    total_count = await get_user_completed_tasks_count(db, user["id"])
    tasks = await get_user_completed_tasks(db, user["id"], limit=limit, offset=offset)

    response_text = format_tasks_message(
        tasks=tasks,
        empty_text=TaskMessages.completed_tasks_empty(),
        header_text=TaskMessages.completed_tasks_header()
    )

    lang = user_lang.get()
    page_word = "Page" if lang == "en" else "Страница"
    from_word = "of" if lang == "en" else "из"
    total_pages = (total_count + limit - 1) // limit
    response_text += f"\n\n📖 <i>{page_word} {page} {from_word} {total_pages}</i>"

    kb = get_pagination_keyboard(total_count, page, limit, "page_completed")

    await callback.message.edit_text(response_text, parse_mode='HTML', reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("page_select:"))
async def page_select_callback(callback: CallbackQuery, db: Connection, user: Row):
    """
    Коллбэк-хэндлер для переключения страниц в результатах поиска (CRUD select).
    """
    page = int(callback.data.split(":")[1])
    limit = 10
    offset = (page - 1) * limit

    search_data = await get_user_search(db, user["id"])
    if not search_data:
        await callback.answer("Результаты поиска не найдены", show_alert=True)
        return

    task_ids, query = search_data
    total_count = len(task_ids)

    tasks = await get_tasks_by_ids(
        db=db,
        task_ids=task_ids,
        user_id=user["id"],
        limit=limit,
        offset=offset
    )

    response_text = TaskMessages.search_results(
        query=query,
        tasks=tasks,
        tz=TIMEZONE
    )

    lang = user_lang.get()
    page_word = "Page" if lang == "en" else "Страница"
    from_word = "of" if lang == "en" else "из"
    total_pages = (total_count + limit - 1) // limit
    response_text += f"\n\n📖 <i>{page_word} {page} {from_word} {total_pages}</i>"

    kb = get_pagination_keyboard(total_count, page, limit, "page_select")

    await callback.message.edit_text(response_text, parse_mode='HTML', reply_markup=kb)
    await callback.answer()
