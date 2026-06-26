from datetime import datetime, timedelta, date
from collections import defaultdict
from aiogram.utils.markdown import html_decoration as hd
from utils.context import user_lang
from config import TIMEZONE
from database.models import TaskStatus


# Дата-заглушка для задач без времени (импортированных из Notion без даты)
_NO_DATE_SENTINEL = date(2060, 1, 1)


def format_date_header(dt: datetime, lang: str) -> str:
    """Минималистичный заголовок даты: 'День недели, число месяц'."""
    weekday = dt.weekday()
    day = dt.day
    month = dt.month

    if lang == "en":
        months_en = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
                      7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"}
        weekdays_en = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"}
        return f"<b>{weekdays_en[weekday]}, {months_en[month]} {day}</b>"
    else:
        months_ru = {1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
                      7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"}
        weekdays_ru = {0: "Понедельник", 1: "Вторник", 2: "Среда", 3: "Четверг", 4: "Пятница", 5: "Суббота", 6: "Воскресенье"}
        return f"<b>{weekdays_ru[weekday]}, {day} {months_ru[month]}</b>"


def _format_no_date_header(lang: str) -> str:
    """Заголовок для группы задач без даты (с датой-заглушкой 01.01.2060)."""
    translations = {
        "ru": "<b>Без даты</b>",
        "en": "<b>No date</b>",
    }
    return translations.get(lang, translations["ru"])


def _is_no_date_sentinel(d: date) -> bool:
    """Проверяет, является ли дата заглушкой (01.01.2060)."""
    return d == _NO_DATE_SENTINEL


def get_importance_section_label(importance: str | None, lang: str) -> str:
    """Заголовок секции важности для группировки задач в списке."""
    translations = {
        "ru": {"high": "Важные", "medium": "Средние", "other": "Остальные"},
        "en": {"high": "Important", "medium": "Medium", "other": "Other"},
    }
    lang_dict = translations.get(lang, translations["ru"])
    key = importance.lower() if importance else "other"
    return lang_dict.get(key, lang_dict["other"])


def format_importance(importance: str | None, lang: str) -> str:
    """Возвращает красивый бейдж уровня важности в зависимости от языка."""
    if not importance:
        return ""

    translations = {
        "ru": {
            "low": "[🟢] Низкий приоритет\n",
            "medium": "[🟡] Важно\n",
            "high": "[🔴] Очень важно\n"
        },
        "en": {
            "low": "[🟢] Low priority\n",
            "medium": "[🟡] Important\n",
            "high": "[🔴] Very important\n"
        }
    }

    lang_dict = translations.get(lang, translations["ru"])
    key = importance.lower()
    return lang_dict.get(key, f"[{importance}]")


IMPORTANCE_ORDER = ("high", "medium", "other")


def _importance_bucket(importance: str | None) -> str:
    """low и None схлопываются в 'other', high/medium остаются отдельными секциями."""
    if importance and importance.lower() in ("high", "medium"):
        return importance.lower()
    return "other"


def compute_local_indices(tasks: list, tz) -> dict[int, int]:
    """
    {task_id: position}, где position — номер задачи внутри СВОЕЙ ДАТЫ,
    с 1 заново на каждый день, в порядке дата -> важность -> время.
    Задачи с датой-заглушкой 01.01.2060 группируются отдельно («Без даты»).
    Единый источник правды: используется и для рендера в Telegram,
    и для контекста, который уходит в ИИ — цифры совпадают 1:1.
    """
    tasks_by_date = defaultdict(list)
    for task in tasks:
        task_datetime = datetime.fromtimestamp(task['time'], tz)
        tasks_by_date[task_datetime.date()].append(task)

    indices: dict[int, int] = {}
    for day_tasks in tasks_by_date.values():
        buckets = defaultdict(list)
        for task in day_tasks:
            importance = task['importance'] if 'importance' in task.keys() else None
            buckets[_importance_bucket(importance)].append(task)

        position = 1
        for bucket_key in IMPORTANCE_ORDER:
            for task in buckets.get(bucket_key, []):
                indices[task['id']] = position
                position += 1

    return indices


def format_tasks_list(tasks: list, tz, lang: str) -> str:
    """
    Группирует задачи по датам и важности, возвращает минималистичный список.
    Задачи с датой-заглушкой 01.01.2060 выводятся в конце под заголовком «Без даты»
    без отображения времени.
    """
    local_indices = compute_local_indices(tasks, tz)

    tasks_by_date = defaultdict(list)
    for task in tasks:
        task_datetime = datetime.fromtimestamp(task['time'], tz)
        tasks_by_date[task_datetime.date()].append((task_datetime, task))

    response_lines = []
    # Обычные даты сортируем по возрастанию; заглушку всегда в конец
    sorted_dates = sorted(
        tasks_by_date.keys(),
        key=lambda d: (1 if _is_no_date_sentinel(d) else 0, d)
    )

    for i, date_key in enumerate(sorted_dates):
        if i > 0:
            response_lines.append("")

        first_dt = tasks_by_date[date_key][0][0]

        # Заголовок группы: обычная дата или «Без даты»
        if _is_no_date_sentinel(date_key):
            response_lines.append(_format_no_date_header(lang))
        else:
            response_lines.append(format_date_header(first_dt, lang))

        # Раскладываем задачи дня по важности, сохраняя порядок внутри секции
        buckets: dict[str, list] = defaultdict(list)
        for task_datetime, task in tasks_by_date[date_key]:
            importance = task['importance'] if 'importance' in task.keys() else None
            buckets[_importance_bucket(importance)].append((task_datetime, task))

        for bucket_key in IMPORTANCE_ORDER:
            bucket_tasks = buckets.get(bucket_key)
            if not bucket_tasks:
                continue

            response_lines.append(f"<b>{get_importance_section_label(bucket_key, lang)}</b>")

            for task_datetime, task in bucket_tasks:
                escaped_content = hd.quote(task['content'])
                is_completed = task['status'] == TaskStatus.COMPLETED.value if 'status' in task.keys() else False
                if is_completed:
                    escaped_content = f"<s>{escaped_content}</s>"

                # Для задач без даты время не показываем
                if _is_no_date_sentinel(date_key):
                    time_str = ""
                else:
                    formatted_time = task_datetime.strftime('%H:%M')
                    if 'duration' in task.keys() and task['duration']:
                        end_datetime = task_datetime + timedelta(minutes=task['duration'])
                        if end_datetime.date() == task_datetime.date():
                            formatted_end = end_datetime.strftime('%H:%M')
                        else:
                            formatted_end = end_datetime.strftime('%d.%m %H:%M')
                        time_str = f"  {formatted_time}–{formatted_end}"
                    else:
                        time_str = f"  {formatted_time}"

                task_line = f"{local_indices[task['id']]}. <b>{escaped_content}</b>{time_str}"
                if task['details']:
                    escaped_details = hd.quote(task['details'])
                    if is_completed:
                        escaped_details = f"<s>{escaped_details}</s>"
                    task_line += f"\n   {escaped_details}"
                task_line += "\n"

                response_lines.append(task_line)

            response_lines.append("")

        if response_lines and response_lines[-1] == "":
            response_lines.pop()

    return "\n".join(response_lines)


def format_tasks_message(tasks: list, empty_text: str) -> str:
    """Форматирует список задач в готовое текстовое сообщение для Telegram с группировкой по датам."""
    if not tasks:
        return empty_text

    lang = user_lang.get()

    formatted_list = format_tasks_list(tasks, TIMEZONE, lang)
    return f"{formatted_list}"


def get_display_end_time(localized_dt: datetime, duration: int | None) -> str | None:
    """Возвращает форматированную строку времени завершения задачи или None."""
    if not duration or duration <= 0:
        return None

    task_end_time = localized_dt + timedelta(minutes=duration)

    if task_end_time.date() == localized_dt.date():
        return task_end_time.strftime('%H:%M')
    return task_end_time.strftime('%Y-%m-%d %H:%M')


def capitalize_first(text: str | None) -> str | None:
    """
    Делает первую букву строки заглавной, не трогая остальные символы.
    В отличие от str.capitalize(), не переводит остаток в нижний регистр.
    """
    if not text:
        return text
    return text[0].upper() + text[1:]