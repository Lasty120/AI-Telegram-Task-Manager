import logging
from datetime import datetime

from aiosqlite import Connection, Row

from .client import NotionClient
from database.crud.task import create_task, get_tasks_by_notion_page_ids, mark_task_as_from_notion

# Временная метка для задач без указанного времени — 01.01.2060 00:00:00 UTC
FALLBACK_TASK_TIMESTAMP = int(datetime(2060, 1, 1, 0, 0, 0).timestamp())


async def _fetch_all_notion_pages(
        client: NotionClient,
        notion_db_id: str,
) -> list[dict]:
    """
    Загружает все страницы из Notion-базы данных с поддержкой пагинации.

    Args:
        client: Авторизованный клиент Notion API.
        notion_db_id: Идентификатор базы данных Notion.

    Returns:
        Список словарей — страниц из Notion.
    """
    pages = []
    has_more = True
    start_cursor = None

    while has_more:
        body: dict = {"page_size": 100}
        if start_cursor:
            body["start_cursor"] = start_cursor

        resp = await client.post(f"/v1/databases/{notion_db_id}/query", json=body)
        if resp.status != 200:
            # Пробуем альтернативный эндпоинт (data_sources)
            resp = await client.post(f"/v1/data_sources/{notion_db_id}/query", json=body)
            if resp.status != 200:
                logging.error(f"Notion fetch: не удалось получить страницы (status={resp.status})")
                break

        data = await resp.json()
        pages.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        start_cursor = data.get("next_cursor")

    return pages


def _extract_title(properties: dict) -> str | None:
    """
    Извлекает название задачи из свойств страницы Notion.
    Ищет поле с типом 'title'.

    Args:
        properties: Словарь свойств страницы из Notion API.

    Returns:
        Строка с заголовком или None если не найдена.
    """
    for prop in properties.values():
        if prop.get("type") == "title":
            rich_text = prop.get("title", [])
            parts = [t.get("plain_text", "") for t in rich_text]
            title = "".join(parts).strip()
            return title if title else None
    return None


def _extract_details(properties: dict) -> str | None:
    """
    Извлекает описание задачи из свойства типа 'rich_text'.

    Args:
        properties: Словарь свойств страницы из Notion API.

    Returns:
        Строка с описанием или None.
    """
    for prop in properties.values():
        if prop.get("type") == "rich_text":
            rich_text = prop.get("rich_text", [])
            parts = [t.get("plain_text", "") for t in rich_text]
            details = "".join(parts).strip()
            return details if details else None
    return None


def _extract_timestamp(properties: dict) -> int:
    """
    Извлекает временную метку из поля типа 'date'.
    Если дата не указана или не парсится — возвращает FALLBACK_TASK_TIMESTAMP (2060 год).

    Args:
        properties: Словарь свойств страницы из Notion API.

    Returns:
        Unix timestamp (int).
    """
    for prop in properties.values():
        if prop.get("type") == "date":
            date_value = prop.get("date")
            if not date_value:
                continue
            start_str = date_value.get("start")
            if not start_str:
                continue
            try:
                # Поддержка форматов: "2024-01-15", "2024-01-15T10:00:00+05:00"
                if "T" in start_str:
                    dt = datetime.fromisoformat(start_str)
                else:
                    dt = datetime.fromisoformat(start_str + "T00:00:00")
                return int(dt.timestamp())
            except (ValueError, TypeError) as e:
                logging.warning(f"Notion fetch: не удалось распарсить дату '{start_str}': {e}")
    return FALLBACK_TASK_TIMESTAMP


def _extract_importance(properties: dict) -> str | None:
    """
    Извлекает важность задачи из поля типа 'select'.
    Нормализует значение к допустимым: 'low', 'medium', 'high'.

    Args:
        properties: Словарь свойств страницы из Notion API.

    Returns:
        Строка 'low' | 'medium' | 'high' или None.
    """
    allowed = {"low", "medium", "high"}

    for prop in properties.values():
        if prop.get("type") == "select":
            select_value = prop.get("select")
            if not select_value:
                continue
            name = (select_value.get("name") or "").strip().lower()
            if name in allowed:
                return name
    return None


def _extract_status(properties: dict) -> str | None:
    """
    Извлекает текущий статус задачи из поля типа 'status' или 'select' с именем 'Status'.

    Args:
        properties: Словарь свойств страницы из Notion API.

    Returns:
        Строка с названием статуса или None.
    """
    for prop_name, prop in properties.items():
        prop_type = prop.get("type")
        if prop_type == "status" or (
                prop_type == "select" and prop_name.strip().lower() == "status"
        ):
            inner = prop.get(prop_type)
            if inner:
                name = (inner.get("name") or "").strip()
                return name if name else None
    return None


def _extract_assignee_ids(properties: dict) -> set[str]:
    """
    Извлекает множество Notion user_id из поля типа 'people'.
    Используется для фильтрации задач по назначенному пользователю.

    Args:
        properties: Словарь свойств страницы из Notion API.

    Returns:
        Множество строк — Notion user_id всех назначенных на задачу.
    """
    for prop in properties.values():
        if prop.get("type") == "people":
            people = prop.get("people", [])
            return {person.get("id") for person in people if person.get("id")}
    return set()


def _is_status_done(status: str | None) -> bool:
    """
    Проверяет, является ли статус задачи «завершённым».
    Считаем завершёнными все статусы, начинающиеся на 'done' (регистронезависимо).

    Args:
        status: Название статуса из Notion или None.

    Returns:
        True если задача завершена и её нужно пропустить.
    """
    if not status:
        return False
    return status.strip().lower().startswith("done")


def _parse_notion_page(page: dict) -> dict | None:
    """
    Преобразует страницу Notion в словарь с полями задачи.
    Возвращает None, если страница архивирована или не имеет заголовка.

    Args:
        page: Словарь страницы из Notion API.

    Returns:
        Словарь с полями задачи (включая assignee_ids) или None если страница не подходит.
    """
    # Пропускаем архивированные страницы
    if page.get("archived") or page.get("in_trash"):
        return None

    properties = page.get("properties", {})
    notion_page_id = page.get("id")

    content = _extract_title(properties)
    if not content:
        # Пропускаем страницы без заголовка — нет смысла создавать пустые задачи
        return None

    notion_status = _extract_status(properties)

    return {
        "notion_page_id": notion_page_id,
        "content": content,
        "details": _extract_details(properties),
        "time": _extract_timestamp(properties),
        "importance": _extract_importance(properties),
        "notion_status": notion_status,
        # Множество ID назначенных пользователей — используется для фильтрации в сервисе
        "assignee_ids": _extract_assignee_ids(properties),
    }


class NotionFetchService:
    """
    Сервис импорта задач из Notion в локальную базу данных.

    Принцип работы:
    - Получает все страницы из Notion-базы пользователя
    - Фильтрует те, что уже есть в локальной БД (по notion_page_id)
    - Создаёт новые записи для отсутствующих задач
    - Помечает их как добавленные из Notion (notion_added=1, notion_page_id заполнен)
    """

    def __init__(self, db: Connection, user: Row):
        """
        Args:
            db: Соединение с базой данных SQLite.
            user: Запись пользователя из БД (Row с полями notion_token, notion_db_id и т.д.).
        """
        self.db = db
        self.user = user

    async def fetch_and_import(self) -> tuple[int, int]:
        """
        Загружает задачи из Notion и сохраняет новые в локальную БД.

        Returns:
            Кортеж (imported_count, skipped_count) — сколько задач импортировано и пропущено.

        Raises:
            ValueError: Если Notion не настроен у пользователя.
        """
        notion_token = self.user["notion_token"]
        notion_db_id = self.user["notion_db_id"]

        if not notion_token or not notion_db_id:
            raise ValueError("Notion не настроен")

        #  Получаем все страницы из Notion
        client = NotionClient(notion_token)
        pages = await _fetch_all_notion_pages(client, notion_db_id)

        if not pages:
            return 0, 0

        # Парсим страницы в удобный формат
        parsed_pages = [_parse_notion_page(p) for p in pages]
        valid_pages = [p for p in parsed_pages if p is not None]

        if not valid_pages:
            return 0, 0

        # Получаем notion_user_id текущего пользователя для фильтрации по assignee
        notion_user_id: str | None = self.user["notion_user_id"] if "notion_user_id" in self.user.keys() else None

        # Применяем бизнес-фильтры:
        #    а) только задачи, назначенные на текущего пользователя (если user_id известен)
        #    б) исключаем задачи со статусом, начинающимся на 'done'
        def _should_import(page: dict) -> bool:
            # Фильтр по assignee — пропускаем только если user_id известен
            if notion_user_id and notion_user_id not in page["assignee_ids"]:
                return False
            # Фильтр по статусу — исключаем завершённые
            if _is_status_done(page.get("notion_status")):
                return False
            return True

        filtered_pages = [p for p in valid_pages if _should_import(p)]
        # Считаем пропущенные по фильтрам (done + чужие) как skipped
        filter_skipped = len(valid_pages) - len(filtered_pages)

        # Получаем список page_id, которые уже есть в локальной БД
        all_page_ids = [p["notion_page_id"] for p in filtered_pages]
        existing_page_ids = await get_tasks_by_notion_page_ids(
            db=self.db,
            notion_page_ids=all_page_ids,
            user_id=self.user["id"]
        )

        # Отфильтровываем уже импортированные задачи
        new_pages = [
            p for p in filtered_pages
            if p["notion_page_id"] not in existing_page_ids
        ]

        skipped_count = filter_skipped + (len(filtered_pages) - len(new_pages))

        if not new_pages:
            return 0, skipped_count

        # Создаём новые задачи в локальной БД
        imported_count = 0
        for page in new_pages:
            try:
                task_id = await create_task(
                    db=self.db,
                    content=page["content"],
                    time=page["time"],
                    user_id=self.user["id"],
                    details=page.get("details"),
                    importance=page.get("importance"),
                    notion_status=page.get("notion_status"),
                )
                # Сразу помечаем задачу как связанную с Notion-страницей
                await mark_task_as_from_notion(
                    db=self.db,
                    task_id=task_id,
                    notion_page_id=page["notion_page_id"]
                )
                imported_count += 1
            except Exception as e:
                logging.error(
                    f"Notion fetch: не удалось создать задачу '{page['content']}': {e}"
                )

        return imported_count, skipped_count
