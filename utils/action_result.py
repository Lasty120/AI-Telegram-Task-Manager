# utils/action_result.py
from dataclasses import dataclass, field
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup

@dataclass
class ActionResult:
    text: str
    keyboard: InlineKeyboardMarkup | ReplyKeyboardMarkup | None = None
    send_separately: bool = False  # True = это сообщение нельзя склеивать с другими
    parse_mode: str = "HTML"
    task_time: str | None = None