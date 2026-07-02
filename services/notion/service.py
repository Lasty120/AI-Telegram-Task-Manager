import aiohttp
from datetime import datetime
from config import TIMEZONE
import logging
from .client import NotionClient
from .utils import find_importance_prop
import asyncio

# Проверка на метку «задача без срока» — чтобы не отправлять 2060 год в Notion
from utils.date_utils import is_fallback_timestamp

# Глобальный словарь для кешировния баз данных Notion. Индексируется по уникальному ID БД
_DB_PROPS_CACHE = {}

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
            await asyncio.sleep(1)

    print(errors)

    return success_count, errors, page_ids


async def _get_db_properties(db_id: str, client: NotionClient) -> dict:
    # 1. Если схема уже есть в кэше, возвращаем её без запроса к API
    if db_id in _DB_PROPS_CACHE:
        return _DB_PROPS_CACHE[db_id]

    # 2. Если в кэше нет, делаем запросы к API
    resp = await client.get(f"/v1/databases/{db_id}")
    if resp.status != 200:
        resp = await client.get(f"/v1/data_sources/{db_id}")
        if resp.status != 200:
            return {}

    data = await resp.json()
    props = {k: v["type"] for k, v in data.get("properties", {}).items()}

    # 3. Сохраняем результат в кэш для будущих задач
    _DB_PROPS_CACHE[db_id] = props
    return props


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
    if date_prop and task.get("time") and not is_fallback_timestamp(task["time"]):
        # Отправляем дату только если у задачи есть реальный срок (не 2060)
        try:
            dt = datetime.fromtimestamp(task["time"], TIMEZONE)
            properties[date_prop] = {"date": {"start": dt.strftime("%Y-%m-%dT%H:%M:%S")}}
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

    # Важность — ищем select-поле с названием, начинающимся на ключевые слова
    # (Важность, Приоритет, Priority, Importance и т.д.) через утилиту find_importance_prop.
    # Не берём произвольный первый select, чтобы не путать с полем Статуса.
    select_prop = find_importance_prop(db_props)
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

    # Статус — ищем первое поле типа "status" или "select" с именем "Status" (регистронезависимо)
    status_prop = next(
        (k for k, v in db_props.items() if v == "status" or (v == "select" and k.strip().lower() == "status")), None
    )
    if status_prop and task.get("notion_status"):
        prop_type = db_props[status_prop]
        properties[status_prop] = {prop_type: {"name": task["notion_status"]}}

    # Мультиселект — ищем первое поле типа "multi_select"
    ms_prop = next(
        (k for k, v in db_props.items() if v == "multi_select"), None
    )
    if ms_prop and task.get("notion_multi_select"):
        properties[ms_prop] = {
            "multi_select": [{"name": task["notion_multi_select"]}]
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
    # Возвращает {"name": <имя свойства>, "options": [...], "groups": [...], "type": <тип>}
    # для первого свойства типа status или select с именем "Status" (регистронезависимо).
    resp = await client.get(f"/v1/databases/{db_id}")
    if resp.status != 200:
        resp = await client.get(f"/v1/data_sources/{db_id}")
        if resp.status != 200:
            return None
    data = await resp.json()
    for name, prop in data.get("properties", {}).items():
        prop_type = prop.get("type")
        if prop_type == "status" or (prop_type == "select" and name.strip().lower() == "status"):
            return {"name": name, **prop.get(prop_type, {}), "type": prop_type}
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
    target_group: str = None,  # "in_progress" | "complete" или произвольный статус
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
        # Сначала пытаемся разрешить через группу статуса (для свойства типа "status")
        option_name = _resolve_status_option(status_schema, target_group)
        
        # Если не разрешилось, пробуем найти опцию с совпадающим именем (регистронезависимо)
        if not option_name:
            options = status_schema.get("options", [])
            matched_option = next(
                (opt["name"] for opt in options if opt["name"].strip().lower() == target_group.strip().lower()),
                None
            )
            if matched_option:
                option_name = matched_option
            else:
                # В качестве крайнего варианта используем значение target_group напрямую как имя статуса
                option_name = target_group

    if not option_name:
        return False

    prop_type = status_schema.get("type", "status")
    body = {"properties": {status_schema["name"]: {prop_type: {"name": option_name}}}}

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
    elif target_group in ("created", "to_do"):
        custom_status_name = user["notion_status_created"] if "notion_status_created" in user.keys() else None
    else:
        # Для поддержки других произвольных статусов используем target_group напрямую
        custom_status_name = target_group

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


async def get_notion_properties_options(notion_token: str, notion_db_id: str) -> dict:
    """
    Возвращает словарь с доступными опциями статуса и первого мультиселекта.
    """
    client = NotionClient(notion_token)
    result = {
        "status_property_name": None,
        "statuses": [],
        "multi_select_property_name": None,
        "multi_selects": []
    }

    # 1. Пробуем стандартный эндпоинт баз данных. Если используешь data_sources — добавь fallback.
    resp = await client.get(f"/v1/databases/{notion_db_id}")

    # Если базы нет, пробуем твой кастомный data_sources (если он нужен для твоей версии API)
    if resp.status != 200:
        resp = await client.get(f"/v1/data_sources/{notion_db_id}")
        if resp.status != 200:
            return result  # Если не нашли ни там, ни там — возвращаем пустышку

    data = await resp.json()
    properties = data.get("properties", {})

    # Ищем статус (тип status ИЛИ тип select с именем 'Status')
    for name, prop in properties.items():
        prop_type = prop.get("type")

        # Если это чистый 'status' ИЛИ 'select' с названием "Status"
        if prop_type == "status" or (prop_type == "select" and name.strip().lower() == "status"):
            result["status_property_name"] = name

            # Динамически получаем внутренние данные ('status' или 'select')
            status_data = prop.get(prop_type, {})
            result["statuses"] = [opt["name"] for opt in status_data.get("options", [])]
            break

    # Ищем первый мультиселект
    for name, prop in properties.items():
        if prop.get("type") == "multi_select":
            result["multi_select_property_name"] = name
            ms_data = prop.get("multi_select", {})
            result["multi_selects"] = [opt["name"] for opt in ms_data.get("options", [])]
            break

    return result


def _build_update_properties(
    db_props: dict,
    task: dict,
    notion_user_id: str | None = None,
) -> dict:
    """
    Формирует свойства для PATCH-запроса обновления страницы в Notion.
    Использует только непустые значения из переданного словаря задачи.
    """
    properties = {}

    # 1. Заголовок (title)
    title_prop = next(
        (k for k, v in db_props.items() if v == "title"),
        None
    )
    if title_prop and task.get("content"):
        properties[title_prop] = {
            "title": [{"text": {"content": task["content"]}}]
        }

    # 2. Дата (date)
    date_prop = next((k for k, v in db_props.items() if v == "date"), None)
    if date_prop and task.get("time"):
        try:
            dt = datetime.fromtimestamp(task["time"], TIMEZONE)
            properties[date_prop] = {"date": {"start": dt.isoformat()}}
        except Exception:
            pass

    # 3. Описание (rich_text)
    text_prop = next(
        (k for k, v in db_props.items() if v == "rich_text"), None
    )
    if text_prop and task.get("details") is not None:
        properties[text_prop] = {
            "rich_text": [{"text": {"content": task["details"]}}]
        }

    # 4. Важность — ищем select-поле с названием из ключевых слов через find_importance_prop.
    # Это гарантирует, что не будет выбрано поле "Статус" или любой другой произвольный select.
    select_prop = find_importance_prop(db_props)
    if select_prop and task.get("importance"):
        properties[select_prop] = {"select": {"name": task["importance"]}}

    # 5. Статус (status или select с именем "status" регистронезависимо)
    status_prop = next(
        (k for k, v in db_props.items() if v == "status" or (v == "select" and k.strip().lower() == "status")), None
    )
    if status_prop and task.get("notion_status"):
        prop_type = db_props[status_prop]
        properties[status_prop] = {prop_type: {"name": task["notion_status"]}}

    # 6. Мультиселект (multi_select)
    ms_prop = next(
        (k for k, v in db_props.items() if v == "multi_select"), None
    )
    if ms_prop and task.get("notion_multi_select"):
        properties[ms_prop] = {
            "multi_select": [{"name": task["notion_multi_select"]}]
        }

    # 7. Пользователь (people)
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

    return properties


async def update_page_in_notion(
    notion_token: str,
    notion_db_id: str,
    page_id: str,
    task_dict: dict,
    notion_user_id: str | None = None,
) -> bool:
    """
    Обновляет существующую страницу задачи в Notion с помощью PATCH-запроса.
    """
    client = NotionClient(notion_token)
    db_props = await _get_db_properties(notion_db_id, client)
    if not db_props:
        return False

    properties = _build_update_properties(db_props, task_dict, notion_user_id)
    if not properties:
        return False

    body = {"properties": properties}
    try:
        resp = await client.patch(f"/v1/pages/{page_id}", json=body)
        return resp.status == 200
    except Exception as e:
        logging.error(f"Notion: ошибка при обновлении страницы {page_id}: {e}")
        return False


async def add_comment_to_notion_page(
        notion_token: str,
        page_id: str,
        comment_text: str,
) -> bool:
    """
    Добавляет page-level комментарий к существующей странице в Notion.

    Требования к интеграции (Notion → my-integrations → Capabilities):
        - Read comments  ✅
        - Insert comments ✅

    Args:
        notion_token (str): Токен Notion-интеграции пользователя.
        page_id (str): UUID страницы Notion, к которой добавляем комментарий.
        comment_text (str): Текст комментария.

    Returns:
        bool: True, если комментарий успешно создан (HTTP 200), иначе False.
    """
    client = NotionClient(notion_token)

    # Формируем тело запроса согласно Notion API Reference
    # https://developers.notion.com/reference/create-a-comment
    body = {
        "parent": {
            "page_id": page_id
        },
        "rich_text": [
            {
                "type": "text",
                "text": {
                    "content": comment_text
                }
            }
        ]
    }

    try:
        resp = await client.post("/v1/comments", json=body)
        if resp.status == 200:
            return True
        # Логируем детали ошибки для диагностики
        data = await resp.json()
        logging.warning(
            f"Notion: не удалось добавить комментарий к странице {page_id}. "
            f"HTTP {resp.status}: {data.get('message', 'Unknown error')}"
        )
        return False
    except Exception as e:
        logging.error(f"Notion: исключение при добавлении комментария к {page_id}: {e}")
        return False


def invalidate_db_cache(db_id: str):
    """Сбрасывает кэш схемы для указанной БД."""
    _DB_PROPS_CACHE.pop(db_id, None)