
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiosqlite import Connection, Row

from services.notion.fetch_service import NotionFetchService
from messages import FetchNotionMessages

router = Router()


@router.message(Command("fetch_notion_tasks"))
async def fetch_notion_tasks_handler(
    message: Message,
    db: Connection,
    user: Row,
) -> None:
    """
    Обработчик команды /fetch_notion_tasks.
    Импортирует задачи из Notion в локальную БД пользователя.
    Задачи, уже существующие в БД (по notion_page_id), пропускаются.
    Время для задач без даты устанавливается на 01.01.2060.
    """
    # Проверяем, настроена ли интеграция с Notion
    if not user["notion_token"] or not user["notion_db_id"]:
        await message.answer(
            text=FetchNotionMessages.notion_not_configured(),
            parse_mode="HTML",
        )
        return

    # Отправляем индикатор загрузки
    waiting_msg = await message.answer(
        text=FetchNotionMessages.fetching_in_progress(),
        parse_mode="HTML",
    )

    try:
        fetch_service = NotionFetchService(db=db, user=user)
        imported_count, skipped_count = await fetch_service.fetch_and_import()

        await waiting_msg.delete()
        await message.answer(
            text=FetchNotionMessages.fetch_result(
                imported=imported_count,
                skipped=skipped_count,
            ),
            parse_mode="HTML",
        )

    except ValueError:
        # Notion не настроен — дублирующая проверка на случай гонки состояний
        await waiting_msg.delete()
        await message.answer(
            text=FetchNotionMessages.notion_not_configured(),
            parse_mode="HTML",
        )

    except Exception as e:
        await waiting_msg.delete()
        await message.answer(
            text=FetchNotionMessages.fetch_error(),
            parse_mode="HTML",
        )
        # Логируем детали для отладки без раскрытия пользователю
        import logging
        logging.error(f"Ошибка при импорте задач из Notion для user={user['id']}: {e}")
