from aiogram import F, Router, Bot
from aiogram.types import Audio, Message

from aiosqlite import Connection, Row

from aiofiles.os import remove, path as aio_path

from services.whisper_service import transcribe_audio
from services.tasks.processor import process_task_command

router = Router()

@router.message(F.voice)
async def handle_voice_message(
        message: Message,
        bot: Bot,
        user: Row,
        db: Connection,
):
    # Даем пользователю понять, что бот принял задачу
    waiting_msg = await message.answer("⏳ Слушаю...")

    # Получаем ID файла и формируем локальное имя файла
    file_id = message.voice.file_id
    file_path = f"{file_id}.ogg"

    try:
        # Скачиваем ГС с серверов Telegram
        file_info = await bot.get_file(file_id)
        await bot.download_file(file_info.file_path, destination=file_path)

        # Отправляем файл в наш сервис транскрибации
        text = await transcribe_audio(file_path)

        # Удаляем сообщение с результатом
        await waiting_msg.delete()
        print(text)

        await process_task_command(
            text=text,
            message=message,
            user=user,
            db=db
        )

    except Exception as e:
        await waiting_msg.edit_text("❌ Произошла ошибка при расшифровке аудио.")
        print(f"Ошибка транскрибации: {e}")

    finally:
        # Очищаем локальный диск от скачанного файла
        if await aio_path.exists(file_path):
            await remove(file_path)