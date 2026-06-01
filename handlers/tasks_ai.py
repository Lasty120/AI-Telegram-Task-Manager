from aiogram import Router, F
from aiogram.types import Message
from aiosqlite import Connection, Row

from services.tasks.processor import process_task_command

router = Router()


@router.message(F.text)
async def process_task_handler(
        message: Message,
        db: Connection,
        user: Row
):
    await process_task_command(
        text=message.text,
        message=message,
        user=user,
        db=db
    )