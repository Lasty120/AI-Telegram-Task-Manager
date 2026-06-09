from datetime import datetime, timedelta
from collections import defaultdict
from aiogram.utils.markdown import html_decoration as hd
from utils.context import user_lang
from config import TIMEZONE


def format_date_header(dt: datetime, lang: str) -> str:
    """Форматирует дату в красивый заголовок с эмодзи и днем недели."""
    weekday = dt.weekday()
    day = dt.day
    month = dt.month
    
    if lang == "en":
        months_en = {
            1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
            7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
        }
        weekdays_en = {
            0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"
        }
        return f"📅 <b>{months_en[month]} {day}, {weekdays_en[weekday]}</b>\n"
    else:
        months_ru = {
            1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
            7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
        }
        weekdays_ru = {
            0: "понедельник", 1: "вторник", 2: "среда", 3: "четверг", 4: "пятница", 5: "суббота", 6: "воскресенье"
        }
        return f"📅 <b>{day} {months_ru[month]}, {weekdays_ru[weekday]}</b>\n"


def format_importance(importance: str | None, lang: str) -> str:
    """Возвращает красивый бейдж уровня важности в зависимости от языка."""
    if not importance:
        return ""
    
    translations = {
        "ru": {
            "low": "🟢",
            "medium": "🟡",
            "most important": "🔴"
        },
        "en": {
            "low": "🟢",
            "medium": "🟡",
            "most important": "🔴T"
        }
    }
    
    lang_dict = translations.get(lang, translations["ru"])
    key = importance.lower()
    return lang_dict.get(key, f"[{importance}]")


def format_tasks_list(tasks: list, tz, lang: str) -> str:
    """Группирует список задач по датам и форматирует их в список с эмодзи."""
    # Группируем задачи по дате
    tasks_by_date = defaultdict(list)
    for task in tasks:
        # Декодируем timestamp в datetime в часовом поясе пользователя
        task_datetime = datetime.fromtimestamp(task['time'], tz)
        task_date = task_datetime.date()
        tasks_by_date[task_date].append((task_datetime, task))
        
    response_lines = []
    
    # Сортируем даты по возрастанию
    sorted_dates = sorted(tasks_by_date.keys())
    
    for i, date_key in enumerate(sorted_dates):
        # Добавляем пустую строку между группами дат (но не перед первой)
        if i > 0:
            response_lines.append("")
            
        # Форматируем заголовок даты
        # Возьмем любой datetime для этой даты (например, первый)
        first_dt = tasks_by_date[date_key][0][0]
        date_header = format_date_header(first_dt, lang)
        response_lines.append(date_header)
        
        for task_datetime, task in tasks_by_date[date_key]:
            escaped_content = hd.quote(task['content'])
            formatted_time = task_datetime.strftime('%H:%M')
            
            if 'duration' in task.keys() and task['duration']:
                end_datetime = task_datetime + timedelta(minutes=task['duration'])
                if end_datetime.date() == task_datetime.date():
                    formatted_end = end_datetime.strftime('%H:%M')
                else:
                    formatted_end = end_datetime.strftime('%d.%m %H:%M')
                
                until_word = "until" if lang == "en" else "до"
                time_str = f"{formatted_time} ({until_word} {formatted_end})"
            else:
                time_str = formatted_time
                
            importance = task['importance'] if 'importance' in task.keys() else None
            imp_str = format_importance(importance, lang)
            
            if imp_str:
                task_line = f"- ⏰ {time_str}. {imp_str} <b>{escaped_content}</b>"
            else:
                task_line = f"- ⏰ {time_str}. <b>{escaped_content}</b>"
            
            if task['details']:
                escaped_details = hd.quote(task['details'])
                task_line += f"\n  └ 📝 <i>{escaped_details}</i>"

            task_line += "\n"
                
            response_lines.append(task_line)
            
    return "\n".join(response_lines)


def format_tasks_message(tasks: list, empty_text: str, header_text: str) -> str:
    """Форматирует список задач в готовое текстовое сообщение для Telegram с группировкой по датам."""
    if not tasks:
        return empty_text

    lang = user_lang.get()
    
    formatted_list = format_tasks_list(tasks, TIMEZONE, lang)
    return f"📋 <b>{header_text}</b>\n\n{formatted_list}"


def get_display_end_time(localized_dt: datetime, duration: int | None) -> str | None:
    """Возвращает форматированную строку времени завершения задачи или None."""
    if not duration or duration <= 0:
        return None

    task_end_time = localized_dt + timedelta(minutes=duration)

    if task_end_time.date() == localized_dt.date():
        return task_end_time.strftime('%H:%M')
    return task_end_time.strftime('%Y-%m-%d %H:%M')