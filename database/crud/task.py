import time
import aiosqlite
from database.models import TaskStatus


async def create_task(db: aiosqlite.Connection, content: str, time: int, user_id: int) -> int:
    """
    Записывает задачу с точным временем unix timestamp, когда должно сработать напоминание.
    """
    async with db.execute(
        """
        INSERT INTO tasks (content, time, user_id) 
        VALUES (?, ?, ?)
        """,
        (content, time, user_id)
    ) as cursor:
        last_id = cursor.lastrowid
    await db.commit()
    return last_id


async def get_user_tasks(db: aiosqlite.Connection, user_id: int) -> list[aiosqlite.Row]:
    """
    Получает все активные задачи конкретного пользователя, отсортированные по времени.
    """
    async with db.execute(
        "SELECT * FROM tasks WHERE user_id = ? AND status = ? ORDER BY time ASC",
        (user_id, TaskStatus.ACTIVE.value)
    ) as cursor:
        return await cursor.fetchall()


async def get_next_task(db: aiosqlite.Connection, user_id: int) -> aiosqlite.Row | None:
    """
    Возвращает самую ближайшую предстоящую активную задачу пользователя.
    Если задач на будущее нет, возвращает None.
    """
    current_now = int(time.time())  # Текущее время в UNIX timestamp

    async with db.execute(
            """
            SELECT *
            FROM tasks
            WHERE user_id = ? AND status = ? AND time > ?
            ORDER BY time ASC
            LIMIT 1
            """,
            (user_id, TaskStatus.ACTIVE.value, current_now)
    ) as cursor:
        return await cursor.fetchone()


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