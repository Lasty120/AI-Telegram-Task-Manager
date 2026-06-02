from datetime import datetime
from aiogram.utils.markdown import html_decoration as hd


def format_tasks_message(tasks: list, empty_text: str, header_text: str) -> str:
    """Форматирует список задач в готовое текстовое сообщение для Telegram."""
    if not tasks:
        return empty_text

    response_lines = [f"📋 {header_text}", ""]

    for index, task in enumerate(tasks, 1):
        # Декодируем timestamp обратно в объект datetime
        task_datetime = datetime.fromtimestamp(task['time'])
        # Форматируем в строку
        formatted_time = task_datetime.strftime('%d.%m %H:%M')

        escaped_content = hd.quote(task['content'])
        task_line = f"{index}. <b>{escaped_content}</b>"
        if 'duration' in task.keys() and task['duration']:
            task_line += f" ({task['duration']} мин)"
        task_line += f" — ⏰ {formatted_time}"

        if task['details']:
            escaped_details = hd.quote(task['details'])
            task_line += f"\n   <i>{escaped_details}</i>"

        response_lines.append(task_line)

    return "\n".join(response_lines)