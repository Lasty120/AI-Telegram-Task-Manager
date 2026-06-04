from contextvars import ContextVar

# По умолчанию язык будет русский
user_lang: ContextVar[str] = ContextVar("user_lang", default="ru")
