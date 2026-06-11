import aiohttp
from datetime import datetime
from config import TIMEZONE


async def add_tasks_to_notion(
    notion_token: str,
    notion_db_id: str,
    tasks: list,
) -> tuple[int, list[str]]:
    """
    Создаёт страницы в Notion для каждой задачи.
    Возвращает (кол-во успешных, список ошибок).
    """
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    # Получаем схему БД — нужно найти поля title, date, text
    db_props = await _get_db_properties(notion_db_id, headers)

    success_count = 0
    errors = []

    async with aiohttp.ClientSession() as session:
        for task in tasks:
            try:
                page_body = _build_page_body(notion_db_id, task, db_props)
                async with session.post(
                    "https://api.notion.com/v1/pages",
                    headers=headers,
                    json=page_body,
                ) as resp:
                    if resp.status == 200:
                        success_count += 1
                    else:
                        err = await resp.json()
                        errors.append(f"{task['content']}: {err.get('message', resp.status)}")
            except Exception as e:
                errors.append(f"{task['content']}: {e}")

    return success_count, errors


async def _get_db_properties(db_id: str, headers: dict) -> dict:
    """Возвращает словарь {prop_name: prop_type} из схемы БД."""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://api.notion.com/v1/databases/{db_id}",
            headers=headers,
        ) as resp:
            if resp.status != 200:
                return {}
            data = await resp.json()
            return {k: v["type"] for k, v in data.get("properties", {}).items()}


def _build_page_body(db_id: str, task, db_props: dict) -> dict:
    """
    Формирует тело запроса /v1/pages.
    Автоматически маппит поля задачи на свойства БД.
    """
    # sqlite3.Row не поддерживает .get() — конвертируем
    if not isinstance(task, dict):
        task = {k: task[k] for k in task.keys()}
    properties = {}

    # Заголовок (title) — есть в каждой Notion DB
    title_prop = next(
        (k for k, v in db_props.items() if v == "title"),
        "Name"  # fallback
    )
    properties[title_prop] = {
        "title": [{"text": {"content": task["content"] or ""}}]
    }

    # Дата — ищем первое поле типа "date"
    date_prop = next((k for k, v in db_props.items() if v == "date"), None)
    if date_prop and task.get("time"):
        try:
            dt = datetime.fromtimestamp(task["time"], TIMEZONE)
            properties[date_prop] = {"date": {"start": dt.isoformat()}}
        except Exception:
            pass

    # Описание — ищем поле типа "rich_text" (не title)
    text_prop = next(
        (k for k, v in db_props.items() if v == "rich_text"), None
    )
    if text_prop and task.get("details"):
        properties[text_prop] = {
            "rich_text": [{"text": {"content": task["details"]}}]
        }

    # Важность — ищем поле типа "select"
    select_prop = next(
        (k for k, v in db_props.items() if v == "select"), None
    )
    if select_prop and task.get("importance"):
        properties[select_prop] = {"select": {"name": task["importance"]}}

    return {
        "parent": {"database_id": db_id},
        "properties": properties,
    }