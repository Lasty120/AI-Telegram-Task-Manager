
from aiogram.utils.markdown import html_decoration as hd
from utils.context import user_lang
from utils.formatters import format_tasks_list
from utils.formatters import format_importance


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
            "ru": "У вас пока нет запланированных задач. Напишите любую задачу, например \"Написать отчет\"",
            "en": "You have no scheduled tasks yet. Write any task, for example \"Write an essay\""
        }
        return translations.get(lang, translations["ru"])


    @classmethod
    def completed_tasks_empty(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "У вас пока нет выполненных задач.",
            "en": "You have no completed tasks yet."
        }
        return translations.get(lang, translations["ru"])



    @classmethod
    def invalid_time_format(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "Некорректный формат времени от ИИ",
            "en": "Invalid time format from AI"
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def task_completed_success(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "Задача успешно выполнена!",
            "en": "Task successfully completed!"
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def task_delayed_success(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "Задача отложена на 15 минут!",
            "en": "Task delayed by 15 minutes!"
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def task_created(cls, content: str, display_time: str, details: str = None, display_end_time: str = None, duration: int = None, importance: str = None) -> str:
        lang = user_lang.get()
        escaped_content = hd.quote(content)
        translations = {
            "ru": {
                "header": f"<code>СОЗДАНО</code>\n<b>{escaped_content}</b> {display_time}\n",
                "until": f"До {display_end_time}",
            },
            "en": {
                "header": f"<code>CREATED</code>\n<b>{escaped_content}</b> {display_time}\n",
                "until": f"Until {display_end_time}",
            },
        }
        t = translations.get(lang, translations["ru"])
        

        imp_str = format_importance(importance, lang)
        
        text = t["header"]
        if imp_str:
            text = f"{imp_str} " + text
            
        if display_end_time:
            text += t["until"]
        if details:
            escaped_details = hd.quote(details)
            text += f"\n<i>{escaped_details}</i>"
        return text

    @classmethod
    def task_update_id_missing(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "Не удалось определить, какую именно задачу нужно изменить.",
            "en": "Failed to identify which specific task to modify."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def task_not_found(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "Задача с таким ID не найдена.",
            "en": "Task with this ID not found."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def task_update_access_denied(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "У вас нет прав на редактирование этой задачи.",
            "en": "You do not have permission to edit this task."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def invalid_update_time_format(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "Некорректный формат времени от ИИ при обновлении.",
            "en": "Invalid time format from AI during update."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def task_updated(cls, content: str, display_time: str, details: str = None, duration: int = None, display_end_time: str = None, importance: str = None) -> str:
        lang = user_lang.get()
        escaped_content = hd.quote(content)
        translations = {
            "ru": {
                "header": f"<code>ОБНОВЛЕНО</code>\n<b>{escaped_content}</b> {display_time}\n",
                "until": f"До {display_end_time}",
            },
            "en": {
                "header": f"<code>UPDATED</code>\n<b>{escaped_content}</b> {display_time}\n",
                "until": f"Until {display_end_time}",
            },
        }
        t = translations.get(lang, translations["ru"])
        
        from utils.formatters import format_importance
        imp_str = format_importance(importance, lang)
        
        text = t["header"]
        if imp_str:
            text = f"{imp_str} " + text
            
        if display_end_time:
            text += t["until"]
        if details:
            escaped_details = hd.quote(details)
            text += f"\n<i>{escaped_details}</i>"
        return text

    @classmethod
    def search_empty(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "По вашему запросу ничего не найдено.",
            "en": "Nothing found for your request."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def search_not_found(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "Задачи не найдены или у вас нет к ним доступа.",
            "en": "Tasks not found or you do not have access to them."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def search_results(cls, query: str, tasks: list, tz) -> str:
        lang = user_lang.get()
        escaped_query = hd.quote(query)
        translations = {
            "ru": {
                "header": f"<b>Результаты поиска по запросу '{escaped_query}':</b>",
            },
            "en": {
                "header": f"<b>Search results for '{escaped_query}':</b>",
            },
        }
        t = translations.get(lang, translations["ru"])
        

        formatted_list = format_tasks_list(tasks, tz, lang)
        
        return f"{t['header']}\n\n{formatted_list}"

    @classmethod
    def task_delete_id_missing(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "Не удалось определить, какую именно задачу нужно завершить.",
            "en": "Failed to identify which specific task to complete."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def task_delete_access_denied(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "У вас нет прав на завершение этой задачи.",
            "en": "You do not have permission to complete this task."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def task_completed(cls, content: str) -> str:
        lang = user_lang.get()
        escaped_content = hd.quote(content)
        translations = {
            "ru": f"<code>✅ ВЫПОЛНЕНО</code>\n<b>{escaped_content}</b>",
            "en": f"<code>✅ COMPLETED</code>\n<b>{escaped_content}</b>",
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def tasks_completed_plural(cls, completed_titles: list) -> str:
        lang = user_lang.get()
        tasks_list_str = ", ".join(f"\"{title}\"" for title in completed_titles)
        translations = {
            "ru": f"<code>✅ ВЫПОЛНЕНО</code>\n{tasks_list_str}",
            "en": f"<code>✅ COMPLETED</code>\n{tasks_list_str}",
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def task_notification(cls, content: str, details: str = None, importance: str = None) -> str:
        lang = user_lang.get()
        escaped_content = hd.quote(content)
        translations = {
            "ru": {
                "header": f"{escaped_content}",
            },
            "en": {
                "header": f"🔔 <b>Reminder:</b>\n{escaped_content}",
            },
        }
        t = translations.get(lang, translations["ru"])

        imp_str = format_importance(importance, lang)
        
        text = t["header"]
        if imp_str:
            text = f"{imp_str} " + text
            
        if details:
            escaped_details = hd.quote(details)
            text += f"\n<i>{escaped_details}</i>"
        return text

    @classmethod
    def task_end_notification(cls, content: str, details: str = None, importance: str = None) -> str:
        """
        ПОТЕНЦИАЛЬНО УДАЛИТЬ
        """
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
        
        from utils.formatters import format_importance
        imp_str = format_importance(importance, lang)
        
        text = t["header"]
        if imp_str:
            text = f"{imp_str} " + text
            
        if details:
            escaped_details = hd.quote(details)
            text += f"\n\n{t['details_label']}\n<i>{escaped_details}</i>"
        return text

    @classmethod
    def conflict_warning(cls, new_task_content: str, new_task_time: str, old_task_content: str, old_task_time: str) -> str:
        lang = user_lang.get()
        escaped_new = hd.quote(new_task_content)
        escaped_old = hd.quote(old_task_content)
        translations = {
            "ru": (
                f"Внимание! {old_task_time} уже занято другой задачей <b>{escaped_old}</b>."
                ),
            "en": (
                f"Warning! {old_task_time} is already occupied by another task <b>{escaped_old}</b>."
            )
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def conflict_resolved_move_old(cls, new_title: str, new_time: str, old_title: str, old_new_time: str) -> str:
        lang = user_lang.get()
        escaped_new = hd.quote(new_title)
        escaped_old = hd.quote(old_title)
        translations = {
            "ru": (
                f"Новая задача <b>{escaped_new}</b> успешно запланирована на выбранное время <b>{new_time}</b>.\n"
                f"Старая задача <b>{escaped_old}</b> перенесена на ближайшее свободное время: <b>{old_new_time}</b>."
            ),
            "en": (
                f"New task <b>{escaped_new}</b> is successfully scheduled at the requested time <b>{new_time}</b>.\n"
                f"Old task <b>{escaped_old}</b> has been moved to the nearest free time: <b>{old_new_time}</b>."
            )
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def conflict_resolved_move_new(cls, new_title: str, new_time: str, old_title: str, old_time: str) -> str:
        lang = user_lang.get()
        escaped_new = hd.quote(new_title)
        escaped_old = hd.quote(old_title)
        translations = {
            "ru": (
                f"Старая задача <b>{escaped_old}</b> сохранена на <b>{old_time}</b>.\n"
                f"Новая задача <b>{escaped_new}</b> перенесена на ближайшее свободное время: <b>{new_time}</b>."
            ),
            "en": (
                f"Old task <b>{escaped_old}</b> remains scheduled at <b>{old_time}</b>.\n"
                f"New task <b>{escaped_new}</b> has been moved to the nearest free time: <b>{new_time}</b>."
            )
        }
        return translations.get(lang, translations["ru"])


    @classmethod
    def conflict_ignore(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "Задачи оставлены параллельно на это время. Расписание сохранено.",
            "en": "Tasks were saved parallely by this time. Schedule were saved."
        }
        return translations.get(lang, translations["ru"])


class AiMessages:
    @classmethod
    def listening(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "Слушаю...",
            "en": "Listening..."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def transcription_error(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "Произошла ошибка при расшифровке аудио.",
            "en": "An error occurred during audio transcription."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def thinking(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "Думаю...",
            "en": "Thinking..."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def no_tasks_found(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "Не нашёл никаких задач в вашем сообщении. Попробуйте написать иначе.",
            "en": "Found no tasks in your message. Please try phrasing it differently."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def execution_error(cls, error_detail: str | None) -> str:
        lang = user_lang.get()
        translations = {
            "ru": {
                "prefix": "Ошибка:",
                "default": "Действие не может быть выполнено (возможно, указана дата в прошлом).",
            },
            "en": {
                "prefix": "Error:",
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
            "ru": f"Не совсем понял, что нужно сделать с '<b>{escaped_content}</b>'.",
            "en": f"Did not completely understand what to do with '<b>{escaped_content}</b>'.",
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


class NotificationMessages:
    @classmethod
    def task_successfully_completed(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "\n\n<code>Выполнено</code>",
            "en": "\n\n.<code>Completed</code>"
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def task_delayed(cls, new_time_dt) -> str:
        lang = user_lang.get()
        translations = {
            "ru": f"\n\n<b>Отложено на 15 минут</b> (до {new_time_dt.strftime('%H:%M')})",
            "en": f"\n\n<b>Delayed by 15 minutes</b> (until {new_time_dt.strftime('%H:%M')})"
        }

        return translations.get(lang, translations["ru"])