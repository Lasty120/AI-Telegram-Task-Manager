import aiohttp
from datetime import datetime
from config import TIMEZONE
import logging
from .client import NotionClient


async def add_tasks_to_notion(
    notion_token: str,
    notion_db_id: str,
    tasks: list,
    notion_user_id: str | None = None,
) -> tuple[int, list[str], dict[int, str]]:
    """
    Создаёт страницы в Notion для каждой задачи.
    Возвращает (кол-во успешных, список ошибок, {task_id: notion_page_id}).
    """
    client = NotionClient(notion_token)
    db_props = await _get_db_properties(notion_db_id, client)

    success_count = 0
    errors = []
    page_ids: dict[int, str] = {}

    async with aiohttp.ClientSession() as session:
        for task in tasks:
            try:
                page_body = _build_page_body(notion_db_id, task, db_props, notion_user_id)
                resp = await client.post(
                    "/v1/pages",
                    session=session,
                    json=page_body,
                )
                if resp.status == 200:
                    data = await resp.json()
                    page_ids[task["id"]] = data["id"]
                    success_count += 1
                else:
                    data = await resp.json()
                    errors.append(f"{task['content']}: {data.get('message', resp.status)}")
            except Exception as e:
                errors.append(f"{task['content']}: {e}")

    return success_count, errors, page_ids


async def _get_db_properties(db_id: str, client: NotionClient) -> dict:
    # Возвращает словарь {prop_name: prop_type} из схемы источника данных Notion 2025.
    resp = await client.get(f"/v1/data_sources/{db_id}")
    if resp.status != 200:
        return {}
    data = await resp.json()
    return {k: v["type"] for k, v in data.get("properties", {}).items()}


def _build_page_body(
    db_id: str,
    task,
    db_props: dict,
    notion_user_id: str | None = None,
) -> dict:
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

    # Создатель — ищем поле типа "people"
    people_prop = next(
        (k for k, v in db_props.items() if v == "people"), None
    )
    if people_prop and notion_user_id:
        properties[people_prop] = {
            "people": [
                {
                    "object": "user",
                    "id": notion_user_id
                }
            ]
        }

    return {
        "parent": {
            "type": "data_source_id",
            "data_source_id": db_id
        },
        "properties": properties,
    }


GROUP_INDEX = {"to_do": 0, "in_progress": 1, "complete": 2}


async def _get_status_property(db_id: str, client: NotionClient) -> dict | None:
    # Возвращает {"name": <имя свойства>, "options": [...], "groups": [...]}
    # для первого свойства типа status в источнике данных, или None, если такого нет.
    resp = await client.get(f"/v1/data_sources/{db_id}")
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


async def get_notion_status_options(notion_token: str, notion_db_id: str) -> list[str]:
    """
    Возвращает список названий опций статуса в базе данных Notion.
    """
    client = NotionClient(notion_token)
    status_schema = await _get_status_property(notion_db_id, client)
    if not status_schema or "options" not in status_schema:
        return []
    return [opt["name"] for opt in status_schema["options"]]


async def update_task_status_in_notion(
    notion_token: str,
    notion_db_id: str,
    page_id: str,
    target_group: str = None,  # "in_progress" | "complete"
    custom_status_name: str = None,
) -> bool:
    """
    Переводит страницу Notion в указанную группу статуса или конкретный статус по имени.
    Возвращает False, если у базы нет свойства status или нужная группа/статус пустой.
    """
    client = NotionClient(notion_token)
    status_schema = await _get_status_property(notion_db_id, client)
    if not status_schema:
        return False

    option_name = custom_status_name
    if not option_name and target_group:
        option_name = _resolve_status_option(status_schema, target_group)

    if not option_name:
        return False

    body = {"properties": {status_schema["name"]: {"status": {"name": option_name}}}}

    resp = await client.patch(f"/v1/pages/{page_id}", json=body)
    return resp.status == 200



async def sync_task_status(user, task, target_group: str):
    """Безопасно обновляет статус задачи в Notion, если она туда добавлена."""
    page_id = task["notion_page_id"] if "notion_page_id" in task.keys() else None
    token = user["notion_token"] if "notion_token" in user.keys() else None
    db_id = user["notion_db_id"] if "notion_db_id" in user.keys() else None

    if not (page_id and token and db_id):
        return

    custom_status_name = None
    if target_group == "complete":
        custom_status_name = user["notion_status_completed"] if "notion_status_completed" in user.keys() else None
    elif target_group == "in_progress":
        custom_status_name = user["notion_status_notified"] if "notion_status_notified" in user.keys() else None

    try:
        ok = await update_task_status_in_notion(
            notion_token=token,
            notion_db_id=db_id,
            page_id=page_id,
            target_group=target_group,
            custom_status_name=custom_status_name,
        )
        if not ok:
            logging.warning(f"Notion: не удалось обновить статус задачи {task['id']}")
    except Exception as e:
        logging.error(f"Notion: ошибка синхронизации статуса задачи {task['id']}: {e}")


async def get_notion_workspace_users(notion_token: str) -> list[dict]:
    """
    Получает список всех участников (пользователей типа person) воркспейса Notion.
    Использует пагинацию в цикле для получения абсолютно всех пользователей.
    """
    client = NotionClient(notion_token)
    users = []
    has_more = True
    start_cursor = None

    async with aiohttp.ClientSession() as session:
        while has_more:
            params = {}
            if start_cursor:
                params["start_cursor"] = start_cursor

            try:
                resp = await client.get("/v1/users", session=session, params=params)
                if resp.status != 200:
                    logging.error(f"Notion API error in get_notion_workspace_users: {resp.status}")
                    break

                data = await resp.json()
                
                # Фильтруем участников, берем только людей (person)
                for u in data.get("results", []):
                    if u.get("type") == "person":
                        name = u.get("name") or "Unknown"
                        email = u.get("person", {}).get("email")
                        users.append({
                            "id": u.get("id"),
                            "name": name,
                            "email": email
                        })

                has_more = data.get("has_more", False)
                start_cursor = data.get("next_cursor")
            except Exception as e:
                logging.error(f"Error calling Notion API in get_notion_workspace_users: {e}")
                break

    # Если людей не нашли, пробуем получить абсолютно всех пользователей (включая ботов и т.д.)
    if not users:
        has_more = True
        start_cursor = None
        async with aiohttp.ClientSession() as session:
            while has_more:
                params = {}
                if start_cursor:
                    params["start_cursor"] = start_cursor
                try:
                    resp = await client.get("/v1/users", session=session, params=params)
                    if resp.status != 200:
                        break
                    data = await resp.json()
                    for u in data.get("results", []):
                        name = u.get("name") or "Unknown"
                        email = u.get("person", {}).get("email") if u.get("type") == "person" else None
                        users.append({
                            "id": u.get("id"),
                            "name": name,
                            "email": email
                        })
                    has_more = data.get("has_more", False)
                    start_cursor = data.get("next_cursor")
                except Exception:
                    break

    return users


async def discover_notion_data_sources(token: str, target_id: str) -> tuple[str | None, list[dict] | None, str | None]:
    """
    Проверяет переданный ID: является ли он контейнером базы данных или конкретным источником данных.
    Возвращает кортеж (type_found, data_sources_list, error_message).
    type_found может быть 'database', 'data_source' или None в случае ошибки.
    """
    client = NotionClient(token)

    # 1. Пробуем запросить как базу данных (контейнер)
    try:
        resp = await client.get(f"/v1/databases/{target_id}")
        if resp.status == 200:
            data = await resp.json()
            data_sources = data.get("data_sources", [])
            return "database", data_sources, None
        elif resp.status != 404 and resp.status != 400:
            try:
                err_data = await resp.json()
                err_msg = err_data.get("message", f"HTTP {resp.status}")
            except Exception:
                err_msg = f"HTTP {resp.status}"
            return None, None, err_msg
    except Exception as e:
        logging.error(f"Notion: ошибка при запросе БД как контейнера: {e}")
        return None, None, str(e)

    # 2. Если получили 404/400, значит это может быть конкретный источник данных (Data Source)
    try:
        resp = await client.get(f"/v1/data_sources/{target_id}")
        if resp.status == 200:
            data = await resp.json()
            title_rich = data.get("title", [])
            name = "".join(t.get("plain_text", "") for t in title_rich) or "Tasks"
            return "data_source", [{"id": data["id"], "name": name}], None
        else:
            try:
                err_data = await resp.json()
                err_msg = err_data.get("message", f"HTTP {resp.status}")
            except Exception:
                err_msg = f"HTTP {resp.status}"
            return None, None, err_msg
    except Exception as e:
        logging.error(f"Notion: ошибка при запросе источника данных: {e}")
        return None, None, str(e)