from datetime import datetime, timedelta
from aiogram.utils.markdown import html_decoration as hd
from utils.context import user_lang


class StartMessages:
    @classmethod
    def welcome(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": (
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
            ),
            "en": (
                "👋 <b>Welcome to the smart task manager!</b>\n\n"
                "I will help you plan your tasks, learn words and remember everything. "
                "You don't need to press complex buttons — just <b>text me</b> or send a <b>voice message</b>, and I will understand and organize everything myself.\n\n"
                "🛠 <b>What I can do:</b>\n\n"
                "📝 <b>Create tasks:</b>\n"
                "• <i>\"Remind me to call mom tomorrow at 18:00\"</i>\n"
                "• <i>\"Learn the word Apple\"</i>\n\n"
                "🔄 <b>Change plans:</b>\n"
                "• <i>\"Move call with Vasya to 19:30\"</i>\n\n"
                "✅ <b>Mark as completed:</b>\n"
                "• <i>\"I bought bread, delete this task\"</i>\n\n"
                "🔍 <b>Search plans:</b>\n"
                "• <i>\"What are my plans for the weekend?\"</i>\n\n"
                "👇 Use the buttons in the menu below to quickly view your active or completed tasks."
            )
        }
        return translations.get(lang, translations["ru"])


class TaskMessages:
    @classmethod
    def tasks_empty(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "У вас пока нет запланированных задач. Используйте /create_task",
            "en": "You have no scheduled tasks yet. Use /create_task"
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def tasks_header(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "<b>Ваш список задач:</b>",
            "en": "<b>Your task list:</b>"
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def completed_tasks_empty(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "У вас пока нет выполненных задач. Используйте /create_task",
            "en": "You have no completed tasks yet. Use /create_task"
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def completed_tasks_header(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "<b>Ваш список выполненных задач:</b>",
            "en": "<b>Your list of completed tasks:</b>"
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def invalid_time_format(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "⚠️ Некорректный формат времени от ИИ",
            "en": "⚠️ Invalid time format from AI"
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def task_completed_success(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "✅ Задача успешно выполнена!",
            "en": "✅ Task successfully completed!"
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def task_delayed_success(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "⏰ Задача отложена на 15 минут!",
            "en": "⏰ Task delayed by 15 minutes!"
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def task_created(cls, content: str, display_time: str, details: str = None, display_end_time: str = None, duration: int = None) -> str:
        lang = user_lang.get()
        escaped_content = hd.quote(content)
        translations = {
            "ru": {
                "header": f"✅ Создана задача: <b>{escaped_content}</b> на {display_time}\n",
                "until": f"До {display_end_time} (Длительность {duration} минут)",
                "details_label": "📖 Детали",
            },
            "en": {
                "header": f"✅ Task created: <b>{escaped_content}</b> for {display_time}\n",
                "until": f"Until {display_end_time} (Duration {duration} minutes)",
                "details_label": "📖 Details",
            },
        }
        t = translations.get(lang, translations["ru"])
        text = t["header"]
        if display_end_time:
            text += t["until"]
        if details:
            escaped_details = hd.quote(details)
            text += f"\n{t['details_label']}: <i>{escaped_details}</i>"
        return text

    @classmethod
    def task_update_id_missing(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "⚠️ Не удалось определить, какую именно задачу нужно изменить.",
            "en": "⚠️ Failed to identify which specific task to modify."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def task_not_found(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "⚠️ Задача с таким ID не найдена.",
            "en": "⚠️ Task with this ID not found."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def task_update_access_denied(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "⚠️ У вас нет прав на редактирование этой задачи.",
            "en": "⚠️ You do not have permission to edit this task."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def invalid_update_time_format(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "⚠️ Некорректный формат времени от ИИ при обновлении.",
            "en": "⚠️ Invalid time format from AI during update."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def task_updated(cls, content: str, display_time: str, details: str = None, duration: int = None, display_end_time: str = None) -> str:
        lang = user_lang.get()
        escaped_content = hd.quote(content)
        translations = {
            "ru": {
                "header": f"🔄 Задача обновлена: <b>{escaped_content}</b> на {display_time}\n",
                "until": f"До {display_end_time} (длительность {duration} минут)",
                "details_label": "📖 Детали",
            },
            "en": {
                "header": f"🔄 Task updated: <b>{escaped_content}</b> for {display_time}\n",
                "until": f"Until {display_end_time} (duration {duration} minutes)",
                "details_label": "📖 Details",
            },
        }
        t = translations.get(lang, translations["ru"])
        text = t["header"]
        if display_end_time:
            text += t["until"]
        if details:
            escaped_details = hd.quote(details)
            text += f"\n{t['details_label']}: <i>{escaped_details}</i>"
        return text

    @classmethod
    def search_empty(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "🔍 По вашему запросу ничего не найдено.",
            "en": "🔍 Nothing found for your request."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def search_not_found(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "🔍 Задачи не найдены или у вас нет к ним доступа.",
            "en": "🔍 Tasks not found or you do not have access to them."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def search_results(cls, query: str, tasks: list, tz) -> str:
        lang = user_lang.get()
        escaped_query = hd.quote(query)
        translations = {
            "ru": {
                "header": f"🔍 <b>Результаты поиска по запросу '{escaped_query}':</b>",
                "until": "до",
            },
            "en": {
                "header": f"🔍 <b>Search results for '{escaped_query}':</b>",
                "until": "until",
            },
        }
        t = translations.get(lang, translations["ru"])
        response_lines = [t["header"], ""]

        for index, task in enumerate(tasks, 1):
            task_datetime = datetime.fromtimestamp(task['time'], tz)
            formatted_time = task_datetime.strftime('%d.%m %H:%M')
            escaped_content = hd.quote(task['content'])

            task_line = f"{index}. <b>{escaped_content}</b>"

            if 'duration' in task.keys() and task['duration']:
                end_datetime = task_datetime + timedelta(minutes=task['duration'])
                if end_datetime.date() == task_datetime.date():
                    formatted_end = end_datetime.strftime('%H:%M')
                else:
                    formatted_end = end_datetime.strftime('%d.%m %H:%M')
                task_line += f" — ⏰ {formatted_time} ({t['until']} {formatted_end})"
            else:
                task_line += f" — ⏰ {formatted_time}"

            if task['details']:
                escaped_details = hd.quote(task['details'])
                task_line += f"\n   <i>{escaped_details}</i>"
            response_lines.append(task_line)
        return "\n".join(response_lines)

    @classmethod
    def task_delete_id_missing(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "⚠️ Не удалось определить, какую именно задачу нужно завершить.",
            "en": "⚠️ Failed to identify which specific task to complete."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def task_delete_access_denied(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "⚠️ У вас нет прав на завершение этой задачи.",
            "en": "⚠️ You do not have permission to complete this task."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def task_completed(cls, content: str) -> str:
        lang = user_lang.get()
        escaped_content = hd.quote(content)
        translations = {
            "ru": f"✅ Задача выполнена:\n <b>{escaped_content}</b>",
            "en": f"✅ Task completed:\n <b>{escaped_content}</b>",
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def tasks_completed_plural(cls, completed_titles: list) -> str:
        lang = user_lang.get()
        tasks_list_str = ", ".join(f"\"{title}\"" for title in completed_titles)
        translations = {
            "ru": f"✅ Задачи выполнены: {tasks_list_str}",
            "en": f"✅ Tasks completed: {tasks_list_str}",
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def task_notification(cls, content: str, details: str = None) -> str:
        lang = user_lang.get()
        escaped_content = hd.quote(content)
        translations = {
            "ru": {
                "header": f"🔔 <b>Напоминание:</b>\n{escaped_content}",
                "details_label": "📝 <b>Детали:</b>",
            },
            "en": {
                "header": f"🔔 <b>Reminder:</b>\n{escaped_content}",
                "details_label": "📝 <b>Details:</b>",
            },
        }
        t = translations.get(lang, translations["ru"])
        text = t["header"]
        if details:
            escaped_details = hd.quote(details)
            text += f"\n\n{t['details_label']}\n<i>{escaped_details}</i>"
        return text

    @classmethod
    def task_end_notification(cls, content: str, details: str = None) -> str:
        lang = user_lang.get()
        escaped_content = hd.quote(content)
        translations = {
            "ru": {
                "header": f"🏁 <b>Задача завершена:</b>\n{escaped_content}",
                "details_label": "📝 <b>Детали:</b>",
            },
            "en": {
                "header": f"🏁 <b>Task completed:</b>\n{escaped_content}",
                "details_label": "📝 <b>Details:</b>",
            },
        }
        t = translations.get(lang, translations["ru"])
        text = t["header"]
        if details:
            escaped_details = hd.quote(details)
            text += f"\n\n{t['details_label']}\n<i>{escaped_details}</i>"
        return text

    @classmethod
    def task_delay(cls, new_dt: str) -> str:
        lang = user_lang.get()
        translations = {
            "ru": f"\n\n⏰ <b>Отложено на 15 минут</b> (до {new_dt})",
            "en": f"\n\n⏰ <b>Delayed by 15 minutes</b> (until {new_dt})",
        }
        return translations.get(lang, translations["ru"])


class AiMessages:
    @classmethod
    def listening(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "⏳ Слушаю...",
            "en": "⏳ Listening..."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def transcription_error(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "❌ Произошла ошибка при расшифровке аудио.",
            "en": "❌ An error occurred during audio transcription."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def thinking(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "🧠 Думаю...",
            "en": "🧠 Thinking..."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def no_tasks_found(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "🤷‍♂️ Не нашёл никаких задач в вашем сообщении. Попробуйте написать иначе.",
            "en": "🤷‍♂️ Found no tasks in your message. Please try phrasing it differently."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def execution_error(cls, error_detail: str | None) -> str:
        lang = user_lang.get()
        translations = {
            "ru": {
                "prefix": "⚠️ Ошибка:",
                "default": "Действие не может быть выполнено (возможно, указана дата в прошлом).",
            },
            "en": {
                "prefix": "⚠️ Error:",
                "default": "Action cannot be performed (possibly date is in the past).",
            },
        }
        t = translations.get(lang, translations["ru"])
        detail = hd.quote(error_detail) if error_detail else t["default"]
        return f"{t['prefix']} {detail}"

    @classmethod
    def unknown_action(cls, content: str) -> str:
        lang = user_lang.get()
        escaped_content = hd.quote(content)
        translations = {
            "ru": f"🤷‍♂️ Не совсем понял, что нужно сделать с '<b>{escaped_content}</b>'.",
            "en": f"🤷‍♂️ Did not completely understand what to do with '<b>{escaped_content}</b>'.",
        }
        return translations.get(lang, translations["ru"])


class LangMessages:
    @classmethod
    def lang_successfully_changed(cls, new_lang: str) -> str:
        lang = new_lang
        translations = {
            "ru": "Язык был успешно изменен!",
            "en": "Language successfully changed."
        }
        return translations.get(lang, translations["ru"])