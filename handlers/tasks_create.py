from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiosqlite import Connection,Row

router = Router()

@router.message(F.text)
async def process_and_save_task_handler(
        message: Message,
        state: FSMContext,
        db: Connection,
        user: Row
):
    user_text = message.text

    await message.answer("Задача принята!")