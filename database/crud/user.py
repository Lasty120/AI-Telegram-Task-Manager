import aiosqlite


async def get_or_create_user(db: aiosqlite.Connection, tg_id: int) -> aiosqlite.Row:
    # 1. Пытаемся найти пользователя
    async with db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
        user = await cursor.fetchone()

    if user:
        return user

    safe_tg_id = int(tg_id)

    # 2. Если не нашли — создаем
    await db.execute(
        "INSERT OR IGNORE INTO users (tg_id) VALUES (?)",
        (safe_tg_id,)
    )
    await db.commit()

    # 3. Возвращаем свежесозданного пользователя
    async with db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
        return await cursor.fetchone()


async def change_language(db: aiosqlite.Connection, tg_id: int, user: aiosqlite.Row):
    safe_tg_id = int(tg_id)
    # Определяем новый язык динамически
    new_lang = "en" if user["lang"] == "ru" else "ru"

    await db.execute(
        "UPDATE users SET lang = ? WHERE tg_id = ?",
        (new_lang, safe_tg_id)
    )

    await db.commit()

    return new_lang


async def update_user_notion(
    db: aiosqlite.Connection,
    tg_id: int,
    notion_token: str | None,
    notion_db_id: str | None,
    notion_status_notified: str | None = None,
    notion_status_completed: str | None = None,
    notion_status_created: str | None = None,
    notion_statuses: str | None = None,
    notion_multi_selects: str | None = None
):
    safe_tg_id = int(tg_id)
    await db.execute(
        """
        UPDATE users 
        SET notion_token = ?, 
            notion_db_id = ?, 
            notion_status_notified = ?, 
            notion_status_completed = ?,
            notion_status_created = ?,
            notion_statuses = ?,
            notion_multi_selects = ?,
            notion_user_id = NULL,
            notion_user_name = NULL
        WHERE tg_id = ?
        """,
        (
            notion_token, 
            notion_db_id, 
            notion_status_notified, 
            notion_status_completed, 
            notion_status_created,
            notion_statuses,
            notion_multi_selects,
            safe_tg_id
        )
    )
    await db.commit()


async def update_user_pending_notion(
    db: aiosqlite.Connection,
    tg_id: int,
    pending_id: str,
    pending_name: str
):
    """
    Обновляет временные (ожидающие одобрения) данные пользователя Notion в БД.
    """
    safe_tg_id = int(tg_id)
    await db.execute(
        """
        UPDATE users 
        SET pending_notion_user_id = ?, 
            pending_notion_user_name = ? 
        WHERE tg_id = ?
        """,
        (pending_id, pending_name, safe_tg_id)
    )
    await db.commit()


async def approve_user_pending_notion(db: aiosqlite.Connection, tg_id: int):
    """
    Одобряет привязку аккаунта Notion: переносит данные из pending в основные колонки.
    """
    safe_tg_id = int(tg_id)
    await db.execute(
        """
        UPDATE users 
        SET notion_user_id = pending_notion_user_id, 
            notion_user_name = pending_notion_user_name,
            pending_notion_user_id = NULL,
            pending_notion_user_name = NULL
        WHERE tg_id = ?
        """,
        (safe_tg_id,)
    )
    await db.commit()


async def reject_user_pending_notion(db: aiosqlite.Connection, tg_id: int):
    """
    Отклоняет привязку аккаунта Notion: очищает временные данные.
    """
    safe_tg_id = int(tg_id)
    await db.execute(
        """
        UPDATE users 
        SET pending_notion_user_id = NULL, 
            pending_notion_user_name = NULL
        WHERE tg_id = ?
        """,
        (safe_tg_id,)
    )
    await db.commit()


async def get_all_users(db: aiosqlite.Connection) -> list[aiosqlite.Row]:
    async with db.execute("SELECT * FROM users") as cursor:
        return await cursor.fetchall()


async def clear_notion_workspace_users(db: aiosqlite.Connection, tg_id: int):
    """
    Удаляет кэш пользователей Notion для указанного Telegram-пользователя.
    """
    safe_tg_id = int(tg_id)
    await db.execute(
        "DELETE FROM notion_workspace_users WHERE tg_id = ?",
        (safe_tg_id,)
    )
    await db.commit()


async def save_notion_workspace_users(db: aiosqlite.Connection, tg_id: int, users: list[dict]):
    """
    Сохраняет пользователей Notion в кэш БД для указанного Telegram-пользователя.
    """
    safe_tg_id = int(tg_id)
    # Формируем список кортежей для пакетной вставки
    data = [
        (safe_tg_id, u["id"], u.get("name"), u.get("email"))
        for u in users
    ]
    if data:
        await db.executemany(
            """
            INSERT OR REPLACE INTO notion_workspace_users (tg_id, notion_user_id, name, email)
            VALUES (?, ?, ?, ?)
            """,
            data
        )
        await db.commit()


async def get_cached_notion_users(db: aiosqlite.Connection, tg_id: int) -> list[dict]:
    """
    Получает закэшированных пользователей Notion для указанного Telegram-пользователя.
    """
    safe_tg_id = int(tg_id)
    async with db.execute(
        "SELECT notion_user_id, name, email FROM notion_workspace_users WHERE tg_id = ?",
        (safe_tg_id,)
    ) as cursor:
        rows = await cursor.fetchall()
        return [
            {
                "id": row["notion_user_id"],
                "name": row["name"],
                "email": row["email"]
            }
            for row in rows
        ]