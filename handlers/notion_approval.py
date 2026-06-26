from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiosqlite import Connection
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.context import FSMContext
import json
from keyboards.inline_keyboards import get_status_selection_keyboard
import logging

from database.crud.user import approve_user_pending_notion, reject_user_pending_notion
from messages import NotionMessages
from config import ADMIN_IDS
from handlers.states import NotionRegistrationStates

router = Router()


# Обработка нажатия кнопки "Одобрить" администратором
@router.callback_query(F.data.startswith("approve_notion:"))
async def process_approve_notion(callback: CallbackQuery, db: Connection, bot: Bot, state: FSMContext):
    # Проверяем, является ли пользователь администратором
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(text="У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    try:
        target_tg_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer(text="Некорректный ID пользователя.", show_alert=True)
        return

    # Получаем данные пользователя для уведомления
    async with db.execute("SELECT * FROM users WHERE tg_id = ?", (target_tg_id,)) as cursor:
        user_row = await cursor.fetchone()

    if not user_row:
        await callback.answer(text="Пользователь не найден в базе данных.", show_alert=True)
        return

    pending_name = user_row["pending_notion_user_name"]
    if not pending_name:
        await callback.answer(text="Нет активного запроса на привязку Notion для этого пользователя.", show_alert=True)
        return

    # Одобряем привязку в базе данных
    await approve_user_pending_notion(db, target_tg_id)

    # Получаем username или имя пользователя для логов/сообщений
    try:
        member = await bot.get_chat(target_tg_id)
        username = member.username
    except Exception:
        username = None

    # Обновляем сообщение администратора
    await callback.message.edit_text(
        text=NotionMessages.notion_admin_approved(username=username, notion_user_name=pending_name),
        parse_mode="HTML"
    )

    await bot.send_message(
        chat_id=target_tg_id,
        text=NotionMessages.registration_success(
            token=user_row["notion_token"],
            db_id=user_row["notion_db_id"],
            created_status=user_row["notion_status_created"],
            completed_status=user_row["notion_status_completed"],
        ),
        parse_mode="HTML"
    )


# Обработка нажатия кнопки "Отклонить" администратором
@router.callback_query(F.data.startswith("reject_notion:"))
async def process_reject_notion(callback: CallbackQuery, db: Connection, bot: Bot):
    # Проверяем, является ли пользователь администратором
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(text="У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    try:
        target_tg_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer(text="Некорректный ID пользователя.", show_alert=True)
        return

    # Получаем данные пользователя для уведомления
    async with db.execute("SELECT * FROM users WHERE tg_id = ?", (target_tg_id,)) as cursor:
        user_row = await cursor.fetchone()

    if not user_row:
        await callback.answer(text="Пользователь не найден в базе данных.", show_alert=True)
        return

    pending_name = user_row["pending_notion_user_name"] or "Unknown"

    # Отклоняем привязку в базе данных
    await reject_user_pending_notion(db, target_tg_id)

    # Получаем username
    try:
        member = await bot.get_chat(target_tg_id)
        username = member.username
    except Exception:
        username = None

    # Обновляем сообщение администратора
    await callback.message.edit_text(
        text=NotionMessages.notion_admin_rejected(username=username, notion_user_name=pending_name),
        parse_mode="HTML"
    )

    # Уведомляем пользователя об отклонении запроса
    try:
        await bot.send_message(
            chat_id=target_tg_id,
            text=NotionMessages.notion_user_rejected_user(),
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление об отклонении пользователю {target_tg_id}: {e}")

    await callback.answer(text="Запрос отклонен.", show_alert=True)
