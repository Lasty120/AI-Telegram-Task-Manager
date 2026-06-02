from datetime import datetime


class StartMessages:
    WELCOME = (
        "👋 <b>Добро пожаловать в умный менеджер задач!</b>\n\n"
        "Я помогу тебе планировать дела, запоминать слова и ничего не забывать. "
        "Тебе не нужно нажимать сложные кнопки — просто <b>напиши мне текст</b> или отправь <b>голосовое сообщение</b>, а я сам всё пойму и организую.\n\n"
        "🛠 <b>Что я умею:</b>\n\n"
        "📝 <b>Создавать задачи:</b>\n"
        "• <i>«Напомни позвонить маме завтра в 18:00»</i>\n"
        "• <i>«Учи слово Apple»</i>\n\n"
        "🔄 <b>Изменять планы:</b>\n"
        "• <i>«Перенеси созвон с Васей на 19:30»</i>\n\n"
        "✅ <b>Отмечать выполненное:</b>\n"
        "• <i>«Я купил хлеб, удали эту задачу»</i>\n\n"
        "🔍 <b>Искать планы:</b>\n"
        "• <i>«Какие у меня планы на выходные?»</i>\n\n"
        "👇 Используй кнопки в меню ниже, чтобы быстро просмотреть свои текущие или завершенные задачи."
    )


class TaskMessages:
    # Task listing (handlers/tasks.py)
    TASKS_EMPTY = "У вас пока нет запланированных задач. Используйте /create_task"
    TASKS_HEADER = "<b>Ваш список задач:</b>"
    COMPLETED_TASKS_EMPTY = "У вас пока нет выполненных задач. Используйте /create_task"
    COMPLETED_TASKS_HEADER = "<b>Ваш список выполненных задач:</b>"
    # Task creation (actions.py)
    INVALID_TIME_FORMAT = "⚠️ Некорректный формат времени от ИИ"

    @staticmethod
    def task_created(content: str, display_time: str, details: str = None, duration: int = None) -> str:
        text = f"✅ Создана задача: {content} на {display_time}"
        if duration:
            text += f" (длительность: {duration} мин)"
        if details:
            text += f"\n📖 Детали: {details}"
        return text

    # Task updating (actions.py)
    TASK_UPDATE_ID_MISSING = "⚠️ Не удалось определить, какую именно задачу нужно изменить."
    TASK_NOT_FOUND = "⚠️ Задача с таким ID не найдена."
    TASK_UPDATE_ACCESS_DENIED = "⚠️ У вас нет прав на редактирование этой задачи."
    INVALID_UPDATE_TIME_FORMAT = "⚠️ Некорректный формат времени от ИИ при обновлении."

    @staticmethod
    def task_updated(content: str, display_time: str, details: str = None, duration: int = None) -> str:
        text = f"🔄 Задача обновлена: {content} на {display_time}"
        if duration:
            text += f" (длительность: {duration} мин)"
        if details:
            text += f"\n📖 Детали: {details}"
        return text

    # Task selection/searching (actions.py)
    SEARCH_EMPTY = "🔍 По вашему запросу ничего не найдено."
    SEARCH_NOT_FOUND = "🔍 Задачи не найдены или у вас нет к ним доступа."

    @staticmethod
    def search_results(query: str, tasks: list, tz) -> str:
        response_lines = [f"🔍 *Результаты поиска по запросу '{query}':*", ""]
        for index, task in enumerate(tasks, 1):
            task_datetime = datetime.fromtimestamp(task['time'], tz)
            formatted_time = task_datetime.strftime('%d.%m %H:%M')
            task_line = f"{index}. *{task['content']}*"
            if 'duration' in task.keys() and task['duration']:
                task_line += f" ({task['duration']} мин)"
            task_line += f" — ⏰ {formatted_time}"
            if task['details']:
                task_line += f"\n   _{task['details']}_"
            response_lines.append(task_line)
        return "\n".join(response_lines)

    # Task completion/deletion (actions.py)
    TASK_DELETE_ID_MISSING = "⚠️ Не удалось определить, какую именно задачу нужно завершить."
    TASK_DELETE_ACCESS_DENIED = "⚠️ У вас нет прав на завершение этой задачи."

    @staticmethod
    def task_completed(content: str) -> str:
        return f"✅ Задача выполнена:\n *{content}*"

    # Scheduler notification (scheduler.py)
    @staticmethod
    def task_notification(content: str, details: str = None) -> str:
        text = f"🔔 <b>Напоминание:</b>\n{content}"
        if details:
            text += f"\n\n📝 <b>Детали:</b>\n{details}"
        return text

    @staticmethod
    def task_end_notification(content: str, details: str = None) -> str:
        text = f"🏁 <b>Задача завершена:</b>\n{content}"
        if details:
            text += f"\n\n📝 <b>Детали:</b>\n{details}"
        return text

    @staticmethod
    def task_delay(new_dt: str) -> str:
        text = f"\n\n⏰ <b>Отложено на 15 минут</b> (до {new_dt})"
        return text


class AiMessages:
    LISTENING = "⏳ Слушаю..."
    TRANSCRIPTION_ERROR = "❌ Произошла ошибка при расшифровке аудио."
    THINKING = "🧠 Думаю..."
    NO_TASKS_FOUND = "🤷‍♂️ Не нашёл никаких задач в вашем сообщении. Попробуйте написать иначе."

    @staticmethod
    def execution_error(error_detail: str | None) -> str:
        detail = error_detail or "Действие не может быть выполнено (возможно, указана дата в прошлом)."
        return f"⚠️ Ошибка: {detail}"

    @staticmethod
    def unknown_action(content: str) -> str:
        return f"🤷‍♂️ Не совсем понял, что нужно сделать с '{content}'."
