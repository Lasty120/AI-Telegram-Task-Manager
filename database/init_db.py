import aiosqlite


async def init_db(db_path: str):
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            details TEXT,
            status INTEGER NOT NULL DEFAULT 0,
            time INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
        """)
        
        # Безопасная автомиграция: добавляем колонку details, если её еще нет
        async with db.execute("PRAGMA table_info(tasks);") as cursor:
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]
            if "details" not in column_names:
                await db.execute("ALTER TABLE tasks ADD COLUMN details TEXT;")
        
        await db.commit()