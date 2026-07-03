"""
handlers/voice_transcriptor.py

Хендлер голосовых сообщений: транскрибирует аудио и обрабатывает как текстовую команду.
"""

import asyncpg
from aiogram import F, Router, Bot
from aiogram.types import Message

from aiofiles.os import remove, path as aio_path

from messages import AiMessages
from database.repositories import TaskRepository, SearchRepository
from services.whisper_service import transcribe_audio
from services.tasks.processor import process_task_command

router = Router()


@router.message(F.voice)
async def handle_voice_message(
        message: Message,
        bot: Bot,
        user: dict,
        db: asyncpg.Connection,
):
    """
    Скачивает голосовое сообщение, транскрибирует через Whisper
    и передаёт текст в процессор задач.
    """
    # Даём пользователю понять, что бот принял сообщение
    waiting_msg = await message.answer(AiMessages.listening())

    file_id = message.voice.file_id
    file_path = f"{file_id}.ogg"

    try:
        # Скачиваем голосовое сообщение с серверов Telegram
        file_info = await bot.get_file(file_id)
        await bot.download_file(file_info.file_path, destination=file_path)

        # Транскрибируем аудио через Whisper
        text = await transcribe_audio(file_path)

        await waiting_msg.delete()

        # Создаём репозитории и передаём в процессор (DI-паттерн)
        task_repo = TaskRepository(db)
        search_repo = SearchRepository(db)

        await process_task_command(
            text=text,
            message=message,
            user=user,
            task_repo=task_repo,
            search_repo=search_repo,
        )

    except Exception as e:
        await waiting_msg.edit_text(AiMessages.transcription_error())
        print(f"Ошибка транскрибации: {e}")

    finally:
        # Удаляем скачанный файл с диска
        if await aio_path.exists(file_path):
            await remove(file_path)