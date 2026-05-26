from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiosqlite import Connection,Row

from services.ai_service import parse_user_text

from database.crud.task import create_task
from services.task_actions import handle_create_task

router = Router()

@router.message(F.text)
async def process_task_handler(
        message: Message,
        db: Connection,
        user: Row
):
        waiting_msg = await message.answer("🧠 Думаю...")

        # Отправляем текст в ИИ
        parsed_command = await parse_user_text(message.text)

        await waiting_msg.delete()

        if isinstance(parsed_command, str):  # Если вернулась ошибка
            await message.answer(parsed_command)
            return

        # МАРШРУТИЗАЦИЯ
        if parsed_command.action == "create":
            await handle_create_task(db=db, user=user, command=parsed_command, message=message)

        elif parsed_command.action == "update":
            await message.answer(f"🔄 Изменяю задачу... (В разработке)")

        elif parsed_command.action == "delete":
            await message.answer(f"🗑 Удаляю задачу... (В разработке)")

        else:
            await message.answer("🤷‍♂️ Не совсем понял, что нужно сделать. Напиши иначе.")