from os import getenv
from dotenv import load_dotenv
import pytz

load_dotenv()

TOKEN = getenv("TG_BOT_TOKEN")
OPENAI_API_KEY = getenv("OPENAI_API_KEY")
OPENAI_DEFAULT_MODEL = getenv("OPENAI_DEFAULT_MODEL")
OPENAI_DEFAULT_URL = getenv("OPENAI_DEFAULT_URL")

DB_PATH = "bot.db" # To delete

GROQ_API_KEY = getenv("GROQ_API_KEY")

TIMEZONE_STR = getenv("TIMEZONE", "Asia/Almaty")
TIMEZONE = pytz.timezone(TIMEZONE_STR)

NOTION_API_KEY = getenv("NOTION_API_KEY")
NOTION_DB_URL = getenv("NOTION_DB_URL")

TASKS_LIMIT_OF_PAGES = 10

ADMIN_IDS_STR = getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_STR.split(",") if x.strip().isdigit()]

# PostgresSQL
DB_HOST = getenv("DB_HOST")
DB_PORT = int(getenv("DB_PORT"))
DB_USER = getenv("DB_USER")
DB_PASS = getenv("DB_PASS")
DB_NAME = getenv("DB_NAME")

def get_database_url():
    return f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

DB_URL = get_database_url()

# Минимальный и максимальный размер пула соединений
POOL_MIN_SIZE = 1
POOL_MAX_SIZE = 10

