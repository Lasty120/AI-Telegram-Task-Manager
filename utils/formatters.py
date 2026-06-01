from datetime import datetime


def format_tasks_message(tasks: list, empty_text: str, header_text: str) -> str:
    """Форматирует список задач в готовое текстовое сообщение для Telegram."""
    if not tasks:
        return empty_text

    response_lines = [f"📋 *{header_text}:*", ""]

    for index, task in enumerate(tasks, 1):
        # Декодируем timestamp обратно в объект datetime
        task_datetime = datetime.fromtimestamp(task['time'])
        # Форматируем в строку
        formatted_time = task_datetime.strftime('%d.%m %H:%M')

        task_line = f"{index}. *{task['content']}* — ⏰ {formatted_time}"

        # Используем .get() для безопасности, если структура task это позволяет
        if task['details']:
            task_line += f"\n   _{task['details']}_"

        response_lines.append(task_line)

    return "\n".join(response_lines)