from aiogram import Router, F
from aiogram.types import Message
from aiosqlite import Connection, Row

from services.ai_service import parse_user_text
from services.task_actions import handle_create_task
from database.crud.task import get_user_tasks

router = Router()


@router.message(F.text)
async def process_task_handler(
        message: Message,
        db: Connection,
        user: Row
):
    waiting_msg = await message.answer("🧠 Думаю...")

    # Получаем текущие задачи пользователя
    user_tasks = await get_user_tasks(db, user["id"])

    # Отправляем текст в ИИ
    parsed_command = await parse_user_text(message.text, user_tasks)

    await waiting_msg.delete()

    if isinstance(parsed_command, str):  # Если вернулась ошибка
        await message.answer(parsed_command)
        return

    tasks = parsed_command.tasks

    if not tasks:
        await message.answer("🤷‍♂️ Не нашёл никаких задач в вашем сообщении. Попробуйте написать иначе.")
        return

    # Обрабатываем каждую распознанную задачу по очереди
    for task_cmd in tasks:
        if task_cmd.action == "create":
            await handle_create_task(db=db, user=user, command=task_cmd, message=message)

        elif task_cmd.action == "update":
            await message.answer(f"🔄 Изменяю задачу '{task_cmd.content}'... (В разработке)")

        elif task_cmd.action == "delete":
            await message.answer(f"🗑 Удаляю задачу '{task_cmd.content}'... (В разработке)")

        else:
            await message.answer(f"🤷‍♂️ Не совсем понял, что нужно сделать с '{task_cmd.content or message.text}'.")