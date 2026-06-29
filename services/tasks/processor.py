"""
services/tasks/processor.py

Точка входа в обработку текстовых команд пользователя.
Изменения (Этап 4):
  - db: Connection заменён на конкретные репозитории (инъекция зависимостей).
  - Удалён прямой вызов database.crud.task.get_user_tasks.
  - Сборка сервисов перенесена на репозитории.
"""

from services.ai.service import parse_user_text
from services.tasks import TaskCRUDService, ConflictService, NotionSyncService, SchedulerService
from database.repositories import TaskRepository, SearchRepository
from messages import AiMessages
from keyboards.reply_keyboards import get_main_kb

from utils.formatters import format_date_header
from config import TIMEZONE
from utils.context import user_lang

from collections import defaultdict
from datetime import datetime
from utils.action_result import ActionResult


async def process_task_command(
    text: str,
    message,
    user: dict,
    task_repo: TaskRepository,
    search_repo: SearchRepository,
) -> None:
    """
    Разбирает текст пользователя через ИИ и выполняет соответствующие действия над задачами.

    Args:
        text (str): Исходный текст сообщения пользователя.
        message: Объект aiogram Message.
        user (dict): Словарь пользователя из БД.
        task_repo (TaskRepository): Репозиторий задач (asyncpg).
        search_repo (SearchRepository): Репозиторий кэша поиска (asyncpg).
    """
    waiting_msg = await message.answer(AiMessages.thinking())

    # Получаем активные задачи пользователя для контекста ИИ
    user_tasks = await task_repo.get_active(user_id=user["id"])
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

    # Собираем все зависимые сервисы через репозитории (DI)
    scheduler_service = SchedulerService(bot=message.bot, user=user)
    notion_service = NotionSyncService(task_repo=task_repo, user=user)
    conflict_service = ConflictService(
        task_repo=task_repo,
        user=user,
        scheduler_service=scheduler_service,
        notion_service=notion_service,
    )
    crud_service = TaskCRUDService(
        task_repo=task_repo,
        search_repo=search_repo,
        user=user,
        bot=message.bot,
        conflict_service=conflict_service,
        scheduler_service=scheduler_service,
        notion_service=notion_service,
    )

    # Собираем результаты: обычные — склеим в одно сообщение, отдельные — по одному
    regular_results: list[ActionResult] = []
    separate_results: list[ActionResult] = []

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
        # Добавление комментария к задаче в Notion — делегируем notion_service,
        # т.к. вся валидация (токен, доступ, page_id) инкапсулирована там
        elif task_cmd.action == "add-comment-to-notion":
            result = await notion_service.add_comment_to_notion(command=task_cmd)
        else:
            result = ActionResult(text=AiMessages.unknown_action(task_cmd.content or text))

        if result.send_separately:
            separate_results.append(result)
        else:
            regular_results.append(result)

    await waiting_msg.delete()

    # Группируем обычные результаты по дате и склеиваем в одно сообщение
    if regular_results:
        grouped: dict = defaultdict(list)
        no_date: list[str] = []

        for r in regular_results:
            if r.task_time:
                dt = datetime.fromisoformat(r.task_time).astimezone(TIMEZONE)
                grouped[dt.date()].append((dt, r.text))
            else:
                no_date.append(r.text)

        lines: list[str] = []
        for date_key in sorted(grouped):
            dt_sample = grouped[date_key][0][0]
            lines.append(format_date_header(dt_sample, user_lang.get()))
            for _, text in grouped[date_key]:
                text += "\n"
                lines.append(text)
        lines.extend(no_date)

        await message.answer("\\n".join(lines), parse_mode="HTML", reply_markup=get_main_kb())

    # Конфликты и результаты select отправляем отдельно — у них своя клавиатура
    for result in separate_results:
        await message.answer(
            result.text,
            parse_mode=result.parse_mode,
            reply_markup=result.keyboard,
        )
