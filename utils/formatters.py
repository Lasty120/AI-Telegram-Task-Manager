from datetime import datetime, timedelta
from aiogram.utils.markdown import html_decoration as hd


def format_tasks_message(tasks: list, empty_text: str, header_text: str) -> str:
    """Форматирует список задач в готовое текстовое сообщение для Telegram."""
    if not tasks:
        return empty_text

    response_lines = [f"📋 {header_text}", ""]

    for index, task in enumerate(tasks, 1):
        # Декодируем timestamp обратно в объект datetime
        task_datetime = datetime.fromtimestamp(task['time'])
        formatted_time = task_datetime.strftime('%d.%m %H:%M')

        escaped_content = hd.quote(task['content'])
        task_line = f"{index}. <b>{escaped_content}</b>"

        # Рассчитываем время окончания, если есть длительность
        if 'duration' in task.keys() and task['duration']:
            end_datetime = task_datetime + timedelta(minutes=task['duration'])
            # Если задача заканчивается в тот же день, выводим только время, иначе - с датой
            if end_datetime.date() == task_datetime.date():
                formatted_end = end_datetime.strftime('%H:%M')
            else:
                formatted_end = end_datetime.strftime('%d.%m %H:%M')

            task_line += f" — ⏰ {formatted_time} (до {formatted_end})"
        else:
            task_line += f" — ⏰ {formatted_time}"

        if task['details']:
            escaped_details = hd.quote(task['details'])
            task_line += f"\n   <i>{escaped_details}</i>"

        response_lines.append(task_line)

    return "\n".join(response_lines)