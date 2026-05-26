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
        "INSERT INTO users (tg_id) VALUES (?)",
        (safe_tg_id,)
    )
    await db.commit()

    # 3. Возвращаем свежесозданного пользователя
    async with db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
        return await cursor.fetchone()