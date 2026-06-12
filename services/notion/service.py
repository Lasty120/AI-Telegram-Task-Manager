import aiohttp
from datetime import datetime
from config import TIMEZONE
import logging


async def add_tasks_to_notion(
    notion_token: str,
    notion_db_id: str,
    tasks: list,
) -> tuple[int, list[str], dict[int, str]]:
    """
    Создаёт страницы в Notion для каждой задачи.
    Возвращает (кол-во успешных, список ошибок, {task_id: notion_page_id}).
    """
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    db_props = await _get_db_properties(notion_db_id, headers)

    success_count = 0
    errors = []
    page_ids: dict[int, str] = {}

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
                        data = await resp.json()
                        page_ids[task["id"]] = data["id"]
                        success_count += 1
                    else:
                        err = await resp.json()
                        errors.append(f"{task['content']}: {err.get('message', resp.status)}")
            except Exception as e:
                errors.append(f"{task['content']}: {e}")

    return success_count, errors, page_ids


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


GROUP_INDEX = {"to_do": 0, "in_progress": 1, "complete": 2}


async def _get_status_property(db_id: str, headers: dict) -> dict | None:
    """
    Возвращает {"name": <имя свойства>, "options": [...], "groups": [...]}
    для первого свойства типа status в базе, или None, если такого нет.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://api.notion.com/v1/databases/{db_id}",
            headers=headers,
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            for name, prop in data.get("properties", {}).items():
                if prop["type"] == "status":
                    return {"name": name, **prop["status"]}
    return None


def _resolve_status_option(status_schema: dict, target_group: str) -> str | None:
    """
    Находит имя первой опции внутри нужной группы (to_do / in_progress / complete).
    """
    groups = status_schema.get("groups", [])
    options = {opt["id"]: opt["name"] for opt in status_schema.get("options", [])}

    index = GROUP_INDEX.get(target_group)
    if index is None or index >= len(groups):
        return None

    option_ids = groups[index].get("option_ids") or []
    if not option_ids:
        return None

    return options.get(option_ids[0])


async def update_task_status_in_notion(
    notion_token: str,
    notion_db_id: str,
    page_id: str,
    target_group: str,  # "in_progress" | "complete"
) -> bool:
    """
    Переводит страницу Notion в указанную группу статуса.
    Возвращает False, если у базы нет свойства status или нужная группа пустая —
    это не ошибка, просто "у этого юзера статусы не настроены так, как мы ожидаем".
    """
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    status_schema = await _get_status_property(notion_db_id, headers)
    if not status_schema:
        return False

    option_name = _resolve_status_option(status_schema, target_group)
    if not option_name:
        return False

    body = {"properties": {status_schema["name"]: {"status": {"name": option_name}}}}

    async with aiohttp.ClientSession() as session:
        async with session.patch(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers=headers,
            json=body,
        ) as resp:
            return resp.status == 200



async def sync_task_status(user, task, target_group: str):
    """Безопасно обновляет статус задачи в Notion, если она туда добавлена."""
    page_id = task["notion_page_id"] if "notion_page_id" in task.keys() else None
    token = user["notion_token"] if "notion_token" in user.keys() else None
    db_id = user["notion_db_id"] if "notion_db_id" in user.keys() else None

    if not (page_id and token and db_id):
        return

    try:
        ok = await update_task_status_in_notion(
            notion_token=token,
            notion_db_id=db_id,
            page_id=page_id,
            target_group=target_group,
        )
        if not ok:
            logging.warning(f"Notion: не удалось обновить статус задачи {task['id']}")
    except Exception as e:
        logging.error(f"Notion: ошибка синхронизации статуса задачи {task['id']}: {e}")