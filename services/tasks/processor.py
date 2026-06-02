from services.ai.service import parse_user_text
from services.tasks.actions import TaskActionsService
from database.crud.task import get_user_tasks

from messages import AiMessages

async def process_task_command(text: str, message, user, db):
    """
    Универсальная функция обработки текстовых команд (введенных вручную или расшифрованных из аудио).
    """
    waiting_msg = await message.answer(AiMessages.THINKING)

    # Получаем текущие задачи пользователя
    user_tasks = await get_user_tasks(db, user["id"])

    # Отправляем текст в ИИ (обрати внимание, передаем аргумент text, а не message.text)
    parsed_command = await parse_user_text(text, user_tasks)

    await waiting_msg.delete()

    if isinstance(parsed_command, str):  # Если вернулась ошибка от нейросети
        await message.answer(parsed_command)
        return

    tasks = parsed_command.tasks

    if not tasks:
        await message.answer(AiMessages.NO_TASKS_FOUND)
        return

    # Инициализируем сервисный класс для обработки задач
    action_service = TaskActionsService(db=db, user=user, bot=message.bot)

    # Обрабатываем каждую распознанную задачу по очереди
    for task_cmd in tasks:
        if task_cmd.action == "create":
            await action_service.create(command=task_cmd, message=message)

        elif task_cmd.action == "update":
            await action_service.update(command=task_cmd, message=message)

        elif task_cmd.action == "select":
            await action_service.select(command=task_cmd, message=message)

        elif task_cmd.action == "forbidden":
            await message.answer(AiMessages.execution_error(task_cmd.content))

        elif task_cmd.action == "delete":
            await action_service.delete(command=task_cmd, message=message)

        else:
            await message.answer(AiMessages.unknown_action(task_cmd.content or text))