
from services.ai.service import parse_user_text
from services.tasks import TaskCRUDService, ConflictService, NotionSyncService, SchedulerService
from database.crud.task import get_user_tasks
from messages import AiMessages
from keyboards.reply_keyboards import get_main_kb

from utils.formatters import format_date_header
from config import TIMEZONE
from utils.context import user_lang

from collections import defaultdict
from datetime import datetime
from utils.action_result import ActionResult


async def process_task_command(text: str, message, user, db):
    waiting_msg = await message.answer(AiMessages.thinking())

    user_tasks = await get_user_tasks(db, user["id"])
    parsed_command = await parse_user_text(text, user_tasks, user)


    if isinstance(parsed_command, str):
        await waiting_msg.delete()
        await message.answer(parsed_command)
        return

    tasks = parsed_command.tasks
    if not tasks:
        await waiting_msg.delete()
        await message.answer(AiMessages.no_tasks_found())
        return

    # Инициализация специализированных сервисов
    scheduler_service = SchedulerService(bot=message.bot, user=user)
    notion_service = NotionSyncService(db=db, user=user)
    conflict_service = ConflictService(
        db=db,
        user=user,
        scheduler_service=scheduler_service,
        notion_service=notion_service
    )
    crud_service = TaskCRUDService(
        db=db,
        user=user,
        bot=message.bot,
        conflict_service=conflict_service,
        scheduler_service=scheduler_service,
        notion_service=notion_service
    )

    # Собираем результаты
    regular_results = []     # Обычные подтверждения — склеим в одно сообщение
    separate_results = []  # Конфликты и select — отдельно каждый

    for task_cmd in tasks:
        if task_cmd.action == "create":
            result = await crud_service.create(command=task_cmd)
        elif task_cmd.action == "update":
            result = await crud_service.update(command=task_cmd)
        elif task_cmd.action == "delete":
            result = await crud_service.delete(command=task_cmd)
        elif task_cmd.action == "select":
            result = await crud_service.select(command=task_cmd)
        elif task_cmd.action == "forbidden":
            result = ActionResult(text=AiMessages.execution_error(task_cmd.content))
        elif task_cmd.action == "add-to-notion":
            result = await notion_service.add_to_notion(command=task_cmd)
        else:
            result = ActionResult(
                text=AiMessages.unknown_action(task_cmd.content or text)
            )

        if result.send_separately:
            separate_results.append(result)
        else:
            regular_results.append(result)

    await waiting_msg.delete()

    # Группируем по дате
    if regular_results:

        grouped = defaultdict(list)
        no_date = []

        for r in regular_results:
            if r.task_time:
                dt = datetime.fromisoformat(r.task_time).astimezone(TIMEZONE)
                grouped[dt.date()].append((dt, r.text))
            else:
                no_date.append(r.text)

        lines = []
        for date_key in sorted(grouped):
            dt_sample = grouped[date_key][0][0]
            lines.append(format_date_header(dt_sample, user_lang.get()))
            for _, text in grouped[date_key]:
                text += "\n"
                lines.append(text)
        lines.extend(no_date)

        await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=get_main_kb())

    # Отправляем конфликты и select отдельно — у них своя клавиатура
    for result in separate_results:
        await message.answer(
            result.text,
            parse_mode=result.parse_mode,
            reply_markup=result.keyboard
        )