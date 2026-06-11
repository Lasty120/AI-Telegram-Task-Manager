from os import getenv
from dotenv import load_dotenv
import pytz

load_dotenv()

TOKEN = getenv("TG_BOT_TOKEN")
OPENAI_API_KEY = getenv("OPENAI_API_KEY")
OPENAI_DEFAULT_MODEL = getenv("OPENAI_DEFAULT_MODEL")
OPENAI_DEFAULT_URL = getenv("OPENAI_DEFAULT_URL")
DB_PATH = "bot.db"
GROQ_API_KEY = getenv("GROQ_API_KEY")

TIMEZONE_STR = getenv("TIMEZONE", "Asia/Almaty")
TIMEZONE = pytz.timezone(TIMEZONE_STR)

NOTION_API_KEY = getenv("NOTION_API_KEY")
NOTION_DB_URL = getenv("NOTION_DB_URL")

TASKS_LIMIT_OF_PAGES = 10
