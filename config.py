from os import getenv
from dotenv import load_dotenv

load_dotenv()

TOKEN = getenv("BOT_TOKEN")
OPENAI_API_KEY = getenv("OPENAI_API_KEY")
OPENAI_DEFAULT_MODEL = getenv("OPENAI_DEFAULT_MODEL")
OPENAI_DEFAULT_URL = getenv("OPENAI_DEFAULT_URL")
DB_PATH = "bot.db"
GROQ_API_KEY = getenv("GROQ_API_KEY")

if not TOKEN:
    exit("Ошибка: BOT_TOKEN не найден в переменной окружения!")
