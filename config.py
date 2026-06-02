from os import getenv
from dotenv import load_dotenv

load_dotenv()

TOKEN = getenv("TG_BOT_TOKEN")
OPENAI_API_KEY = getenv("GOOGLE_API_KEY") # Заменил на гугл вместо OPENAI_API_KEY для тестов
OPENAI_DEFAULT_MODEL = getenv("OPENAI_DEFAULT_MODEL")
OPENAI_DEFAULT_URL = getenv("OPENAI_DEFAULT_URL")
DB_PATH = "bot.db"
GROQ_API_KEY = getenv("GROQ_API_KEY")


