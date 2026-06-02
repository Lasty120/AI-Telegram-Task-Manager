from config import GROQ_API_KEY
from groq import AsyncGroq
import aiofiles

# Инициализируем клиента. Ключ берется из переменных окружения
WHISPER_MODEL = "whisper-large-v3-turbo"
client = AsyncGroq(api_key=GROQ_API_KEY)

async def transcribe_audio(file_path: str) -> str:
    """Отправляет аудиофайл в Groq Whisper и возвращает текст."""
    # Открываем и читаем файл асинхронно, не блокируя другие задачи бота
    async with aiofiles.open(file_path, "rb") as file:
        audio_bytes = await file.read()

    transcription = await client.audio.transcriptions.create(
        file=(file_path, audio_bytes),
        model=WHISPER_MODEL,
        response_format="text"
    )
    return transcription