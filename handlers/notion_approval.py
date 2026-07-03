"""
handlers/notion_approval.py

Хендлеры для одобрения/отклонения привязки аккаунта Notion администратором.
Изменения (Этап 5):
  - aiosqlite убран, принимаем asyncpg.Connection.
  - Прямые SQL db.execute("SELECT * FROM users WHERE tg_id = ?") заменены
    на user_repo.get_by_tg_id().
  - approve_user_pending_notion / reject_user_pending_notion
    заменены на user_repo.approve_pending_notion / user_repo.reject_pending_notion.
  - UserRepository создаётся прямо в каждом хендлере (DI-паттерн).
"""

import logging

import asyncpg
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

from database.repositories import UserRepository
from messages import NotionMessages
from config import ADMIN_IDS

router = Router()


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательный метод для проверки прав и извлечения контекста
# ─────────────────────────────────────────────────────────────────────────────

async def _get_admin_action_context(callback: CallbackQuery, db: asyncpg.Connection, bot: Bot):
    """
    Проверяет права администратора, извлекает ID, достает данные пользователя из БД и Telegram.
    Возвращает (target_tg_id, user_repo, user_row, username).
    Если возникает ошибка, отправляет уведомление и возвращает (None, None, None, None).
    """
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(text="У вас нет прав для выполнения этого действия.", show_alert=True)
        return None, None, None, None

    try:
        target_tg_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer(text="Некорректный ID пользователя.", show_alert=True)
        return None, None, None, None

    user_repo = UserRepository(db)
    user_row = await user_repo.get_by_tg_id(target_tg_id)

    if not user_row:
        await callback.answer(text="Пользователь не найден в базе данных.", show_alert=True)
        return None, None, None, None

    try:
        member = await bot.get_chat(target_tg_id)
        username = member.username
    except Exception:
        username = None

    return target_tg_id, user_repo, user_row, username


# ─────────────────────────────────────────────────────────────────────────────
# Одобрение привязки Notion администратором
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("approve_notion:"))
async def process_approve_notion(
        callback: CallbackQuery,
        db: asyncpg.Connection,
        bot: Bot,
):
    """
    Одобряет привязку аккаунта Notion: переносит pending-данные в основные колонки.
    """
    target_tg_id, user_repo, user_row, username = await _get_admin_action_context(callback, db, bot)
    if target_tg_id is None:
        return  # Ошибка уже обработана во вспомогательном методе

    pending_name = user_row.get("pending_notion_user_name")
    if not pending_name:
        await callback.answer(
            text="Нет активного запроса на привязку Notion для этого пользователя.",
            show_alert=True,
        )
        return

    # Атомарно переносим pending-данные в основные колонки
    await user_repo.approve_pending_notion(target_tg_id)

    # Обновляем сообщение администратора
    await callback.message.edit_text(
        text=NotionMessages.notion_admin_approved(
            username=username,
            notion_user_name=pending_name,
        ),
        parse_mode="HTML",
    )

    # Уведомляем пользователя об одобрении
    await bot.send_message(
        chat_id=target_tg_id,
        text=NotionMessages.registration_success(
            token=user_row.get("notion_token"),
            db_id=user_row.get("notion_db_id"),
            created_status=user_row.get("notion_status_created"),
            completed_status=user_row.get("notion_status_completed"),
        ),
        parse_mode="HTML",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Отклонение привязки Notion администратором
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("reject_notion:"))
async def process_reject_notion(
        callback: CallbackQuery,
        db: asyncpg.Connection,
        bot: Bot,
):
    """
    Отклоняет привязку аккаунта Notion: очищает pending-данные без переноса.
    """
    target_tg_id, user_repo, user_row, username = await _get_admin_action_context(callback, db, bot)
    if target_tg_id is None:
        return  # Ошибка уже обработана во вспомогательном методе

    pending_name = user_row.get("pending_notion_user_name") or "Unknown"

    # Очищаем pending-данные без переноса
    await user_repo.reject_pending_notion(target_tg_id)

    # Обновляем сообщение администратора
    await callback.message.edit_text(
        text=NotionMessages.notion_admin_rejected(
            username=username,
            notion_user_name=pending_name,
        ),
        parse_mode="HTML",
    )

    # Уведомляем пользователя об отклонении
    try:
        await bot.send_message(
            chat_id=target_tg_id,
            text=NotionMessages.notion_user_rejected_user(),
            parse_mode="HTML",
        )
    except Exception as e:
        logging.error(
            f"Не удалось отправить уведомление об отклонении пользователю {target_tg_id}: {e}"
        )

    await callback.answer(text="Запрос отклонён.", show_alert=True)