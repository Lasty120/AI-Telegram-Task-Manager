
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
    def task_created(cls, content: str, display_time: str, details: str = None, display_end_time: str = None, importance: str = None) -> str:
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
    def task_updated(cls, content: str, display_time: str, details: str = None, display_end_time: str = None, importance: str = None) -> str:
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


class NotionMessages:
    @classmethod
    def start_registration(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": (
                "<b>Регистрация Notion</b>\n\n"
                "Чтобы связать бота с вашим Notion, пожалуйста, отправьте ваш <b>Notion Integration Token</b> (Internal Integration Token).\n\n"
                "Вы можете создать интеграцию на странице <a href='https://www.notion.so/my-integrations'>notion.so/my-integrations</a>.\n\n"
                "Если вы хотите пропустить этот шаг, отправьте /skip или нажмите кнопку.\n"
                "Для отмены отправьте /cancel или нажмите кнопку."
            ),
            "en": (
                "<b>Notion Registration</b>\n\n"
                "To link the bot to your Notion, please send your <b>Notion Integration Token</b> (Internal Integration Token).\n\n"
                "You can create an integration at <a href='https://www.notion.so/my-integrations'>notion.so/my-integrations</a>.\n\n"
                "If you want to skip this step, send /skip or press the button.\n"
                "To cancel, send /cancel or press the button."
            )
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def invalid_token(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": (
                "<b>Неверный формат токена!</b>\n\n"
                "Токен Notion должен начинаться с <code>secret_</code>.\n"
                "Пожалуйста, отправьте корректный токен, пропустите шаг с помощью /skip или отмените регистрацию с помощью /cancel."
            ),
            "en": (
                "<b>Invalid token format!</b>\n\n"
                "Notion token must start with <code>secret_</code>.\n"
                "Please send a valid token, skip this step with /skip, or cancel with /cancel."
            )
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def ask_db_id(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": (
                "<b>Укажите ID или ссылку на базу данных Notion</b>\n\n"
                "Пожалуйста, отправьте ссылку на вашу базу данных задач Notion или её ID.\n"
                "ID автоматически извлечётся из ссылки вида:\n"
                "<code>https://www.notion.so/[DATABASE_ID]?v=...</code>\n\n"
                "Не забудьте поделиться (Share) вашей базой данных с созданной интеграцией в самом Notion!\n\n"
                "Отправьте ссылку/ID, пропустите шаг с помощью /skip или отмените с помощью /cancel."
            ),
            "en": (
                "<b>Provide Notion Database ID or URL</b>\n\n"
                "Please send the URL of your Notion tasks database or its ID.\n"
                "The ID will be automatically extracted from URLs like:\n"
                "<code>https://www.notion.so/[DATABASE_ID]?v=...</code>\n\n"
                "Don't forget to share your database with the created integration in Notion!\n\n"
                "Send the URL/ID, skip with /skip, or cancel with /cancel."
            )
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def invalid_db_id(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": (
                "<b>Не удалось найти ID базы данных в вашем сообщении!</b>\n\n"
                "Убедитесь, что вы отправили корректную ссылку Notion или 32-значный ID (состоящий из букв a-f и цифр).\n"
                "Пожалуйста, попробуйте снова, пропустите шаг (/skip) или отмените (/cancel)."
            ),
            "en": (
                "<b>Could not find Database ID in your message!</b>\n\n"
                "Make sure you sent a valid Notion URL or a 32-character hex ID (consisting of letters a-f and digits).\n"
                "Please try again, skip this step (/skip), or cancel (/cancel)."
            )
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def connection_failed(cls, error_msg: str) -> str:
        lang = user_lang.get()
        translations = {
            "ru": (
                "<b>Не удалось связаться с Notion!</b>\n\n"
                f"Ошибка от Notion: <code>{error_msg}</code>\n\n"
                "Пожалуйста, убедитесь, что:\n"
                "1. Токен интеграции скопирован без ошибок.\n"
                "2. Ссылка/ID базы данных указаны верно.\n"
                "3. <b>Важно:</b> Вы открыли доступ интеграции к этой базе данных в Notion (через Connections в верхнем правом меню базы данных).\n\n"
                "Давайте попробуем настроить заново. Пожалуйста, отправьте ваш Notion Integration Token:"
            ),
            "en": (
                "<b>Failed to connect to Notion!</b>\n\n"
                f"Error from Notion: <code>{error_msg}</code>\n\n"
                "Please ensure that:\n"
                "1. The integration token is copied correctly.\n"
                "2. The database URL/ID is correct.\n"
                "3. <b>Important:</b> You have granted connection access to the integration on the database page in Notion.\n\n"
                "Let's start the configuration again. Please send your Notion Integration Token:"
            )
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def verifying_connection(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "<b>Проверяем соединение с Notion...</b> Пожалуйста, подождите.",
            "en": "<b>Checking connection with Notion...</b> Please wait."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def registration_cancelled(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "Регистрация Notion отменена.",
            "en": "Notion registration cancelled."
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def registration_success(cls, token: str | None, db_id: str | None) -> str:
        lang = user_lang.get()
        token_str = token[:4] + "..." + token[-4:] if token else "—"
        db_id_str = db_id if db_id else "—"
        translations = {
            "ru": (
                "<b>Регистрация Notion успешно завершена!</b>\n\n"
                f"• Ключ интеграции: <code>{token_str}</code>\n"
                f"• ID базы данных: <code>{db_id_str}</code>\n\n"
                "Все настройки сохранены. Теперь ваши задачи могут синхронизироваться с Notion."
            ),
            "en": (
                "<b>Notion registration completed successfully!</b>\n\n"
                f"• Integration Key: <code>{token_str}</code>\n"
                f"• Database ID: <code>{db_id_str}</code>\n\n"
                "All settings saved. Now your tasks can synchronize with Notion."
            )
        }
        return translations.get(lang, translations["ru"])


    @classmethod
    def not_configured(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": (
                "Notion не подключён. Используйте /start_registration, "
                "чтобы привязать свою базу данных."
            ),
            "en": (
                "Notion is not connected. Use /start_registration "
                "to link your database."
            ),
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def no_tasks_to_send(cls) -> str:
        lang = user_lang.get()
        translations = {
            "ru": "Не смог определить, какие задачи отправить в Notion.",
            "en": "Could not determine which tasks to send to Notion.",
        }
        return translations.get(lang, translations["ru"])

    @classmethod
    def tasks_sent(cls, success_count: int, total: int, errors: list) -> str:
        lang = user_lang.get()
        if lang == "en":
            text = f"<b>Sent to Notion: {success_count}/{total}</b>"
            if errors:
                joined = "\n".join(f"• {e}" for e in errors[:3])
                text += f"\n\nErrors:\n{joined}"
        else:
            text = f"<b>Отправлено в Notion: {success_count}/{total}</b>"
            if errors:
                joined = "\n".join(f"• {e}" for e in errors[:3])
                text += f"\n\nОшибки:\n{joined}"
        return text