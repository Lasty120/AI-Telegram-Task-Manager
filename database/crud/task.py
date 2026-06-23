import time
import aiosqlite
from database.models import TaskStatus


async def create_task(
        db: aiosqlite.Connection,
        content: str,
        time: int,
        user_id: int,
        details: str = None,
        duration: int = None,
        importance: str = None,
        notion_status: str = None,
        notion_multi_select: str = None
) -> int:
    """
    Записывает задачу с точным временем unix timestamp, когда должно сработать напоминание.
    """
    async with db.execute(
        """
        INSERT INTO tasks (content, details, time, user_id, duration, importance, notion_status, notion_multi_select) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (content, details, time, user_id, duration, importance, notion_status, notion_multi_select)
    ) as cursor:
        last_id = cursor.lastrowid
    await db.commit()
    return last_id


async def get_user_tasks(
    db: aiosqlite.Connection, 
    user_id: int, 
    limit: int = None, 
    offset: int = None
) -> list[aiosqlite.Row]:
    """
    Получает активные задачи конкретного пользователя, отсортированные по времени.
    Поддерживает пагинацию с помощью параметров limit и offset.
    """
    query = "SELECT * FROM tasks WHERE user_id = ? AND status = ? ORDER BY time ASC"
    params = [user_id, TaskStatus.ACTIVE.value]
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)
    if offset is not None:
        query += " OFFSET ?"
        params.append(offset)
        
    async with db.execute(query, tuple(params)) as cursor:
        return await cursor.fetchall()


async def get_user_tasks_count(db: aiosqlite.Connection, user_id: int) -> int:
    """
    Возвращает общее количество активных задач пользователя (для подсчета количества страниц).
    """
    async with db.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = ?",
        (user_id, TaskStatus.ACTIVE.value)
    ) as cursor:
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_user_completed_tasks(
    db: aiosqlite.Connection, 
    user_id: int, 
    limit: int = None, 
    offset: int = None
) -> list[aiosqlite.Row]:
    """
    Получает выполненные задачи конкретного пользователя, отсортированные по времени.
    Поддерживает пагинацию с помощью параметров limit и offset.
    """
    query = "SELECT * FROM tasks WHERE user_id = ? AND status = ? ORDER BY time ASC"
    params = [user_id, TaskStatus.COMPLETED.value]
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)
    if offset is not None:
        query += " OFFSET ?"
        params.append(offset)
        
    async with db.execute(query, tuple(params)) as cursor:
        return await cursor.fetchall()


async def get_user_completed_tasks_count(db: aiosqlite.Connection, user_id: int) -> int:
    """
    Возвращает общее количество выполненных задач пользователя (для подсчета количества страниц).
    """
    async with db.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = ?",
        (user_id, TaskStatus.COMPLETED.value)
    ) as cursor:
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_due_tasks(db: aiosqlite.Connection) -> list[aiosqlite.Row]:
    current_time = int(time.time())
    async with db.execute(
        """
        SELECT tasks.id, tasks.content, users.tg_id 
        FROM tasks 
        JOIN users ON tasks.user_id = users.id 
        WHERE tasks.time <= ? AND tasks.status = ?
        """,
        (current_time, TaskStatus.ACTIVE.value)  # status = 0
    ) as cursor:
        return await cursor.fetchall()


async def complete_task(db: aiosqlite.Connection, task_id: int):
    await db.execute(
        "UPDATE tasks SET status = ? WHERE id = ?",
        (TaskStatus.COMPLETED.value, task_id)  # статус станет 1
    )
    await db.commit()


async def get_task_by_id(db: aiosqlite.Connection, task_id: int) -> aiosqlite.Row | None:
    async with db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)) as cursor:
        return await cursor.fetchone()


async def get_tasks_by_ids(
        db: aiosqlite.Connection,
        task_ids: list[int],
        user_id: int,
        limit: int = None,
        offset: int = None
) -> list[aiosqlite.Row]:
    """
    Получает список задач по их ID для конкретного пользователя с поддержкой лимита и смещения.
    """
    if not task_ids:
        return []
    placeholders = ', '.join('?' for _ in task_ids)
    query = f"SELECT * FROM tasks WHERE id IN ({placeholders}) AND user_id = ? ORDER BY time ASC"
    params = list(task_ids) + [user_id]
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)
    if offset is not None:
        query += " OFFSET ?"
        params.append(offset)

    async with db.execute(query, tuple(params)) as cursor:
        tasks = await cursor.fetchall()
    return tasks


async def save_user_search(db: aiosqlite.Connection, user_id: int, task_ids: list[int], query: str):
    """
    Кэширует список найденных ID задач для пользователя для последующей постраничной навигации.
    """
    task_ids_str = ",".join(map(str, task_ids))
    await db.execute(
        """
        INSERT OR REPLACE INTO user_searches (user_id, task_ids, query)
        VALUES (?, ?, ?)
        """,
        (user_id, task_ids_str, query)
    )
    await db.commit()


async def get_user_search(db: aiosqlite.Connection, user_id: int) -> tuple[list[int], str] | None:
    """
    Извлекает из кэша сохраненные ID задач и исходный поисковый запрос пользователя.
    """
    async with db.execute(
        "SELECT task_ids, query FROM user_searches WHERE user_id = ?",
        (user_id,)
    ) as cursor:
        row = await cursor.fetchone()
        if row:
            task_ids = [int(x) for x in row[0].split(",") if x]
            return task_ids, row[1]
        return None


async def update_task(
    db: aiosqlite.Connection,
    task_id: int,
    content: str = None,
    details: str = None,
    time_val: int = None,
    duration: int = None,
    importance: str = None,
    notion_status: str = None,
    notion_multi_select: str = None
):
    updates = []
    params = []
    if content is not None:
        updates.append("content = ?")
        params.append(content)
    if details is not None:
        updates.append("details = ?")
        params.append(details)
    if time_val is not None:
        updates.append("time = ?")
        params.append(time_val)
    if duration is not None:
        updates.append("duration = ?")
        params.append(duration)
    if importance is not None:
        updates.append("importance = ?")
        params.append(importance)
    if notion_status is not None:
        updates.append("notion_status = ?")
        params.append(notion_status)
    if notion_multi_select is not None:
        updates.append("notion_multi_select = ?")
        params.append(notion_multi_select)
        
    if not updates:
        return
        
    params.append(task_id)
    query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
    await db.execute(query, tuple(params))
    await db.commit()


async def mark_tasks_notion_added(db: aiosqlite.Connection, task_ids: list[int]):
    """Помечает задачи как добавленные в Notion."""
    if not task_ids:
        return
    placeholders = ", ".join("?" for _ in task_ids)
    await db.execute(
        f"UPDATE tasks SET notion_added = 1 WHERE id IN ({placeholders})",
        tuple(task_ids)
    )
    await db.commit()


async def  set_task_notion_page_id(db: aiosqlite.Connection, task_id: int, page_id: str):
    """Сохраняет ID страницы Notion и помечает задачу как добавленную."""
    await db.execute(
        "UPDATE tasks SET notion_added = 1, notion_page_id = ? WHERE id = ?",
        (page_id, task_id)
    )
    await db.commit()


async def get_user_today_tasks(
    db: aiosqlite.Connection, 
    user_id: int, 
    start_time: int,
    end_time: int,
    limit: int = None, 
    offset: int = None
) -> list[aiosqlite.Row]:
    """
    Получает все задачи (активные и выполненные) конкретного пользователя за указанный интервал времени (сегодня).
    Поддерживает пагинацию с помощью параметров limit и offset.
    """
    query = "SELECT * FROM tasks WHERE user_id = ? AND time >= ? AND time <= ? ORDER BY time ASC"
    params = [user_id, start_time, end_time]
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)
    if offset is not None:
        query += " OFFSET ?"
        params.append(offset)
        
    async with db.execute(query, tuple(params)) as cursor:
        return await cursor.fetchall()


async def get_user_today_tasks_count(
    db: aiosqlite.Connection, 
    user_id: int,
    start_time: int,
    end_time: int
) -> int:
    """
    Возвращает общее количество задач пользователя за указанный интервал времени (сегодня).
    """
    async with db.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND time >= ? AND time <= ?",
        (user_id, start_time, end_time)
    ) as cursor:
        row = await cursor.fetchone()
        return row[0] if row else 0