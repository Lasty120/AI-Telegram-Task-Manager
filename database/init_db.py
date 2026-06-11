import aiosqlite


async def init_db(db_path: str):
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER UNIQUE NOT NULL,
            lang TEXT DEFAULT 'ru',
            notion_db_id TEXT,
            notion_token TEXT
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            details TEXT,
            status INTEGER NOT NULL DEFAULT 0,
            time INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            duration INTEGER,
            importance TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );

        -- Таблица для кэширования последних результатов поиска (выбора) пользователя с целью пагинации
        CREATE TABLE IF NOT EXISTS user_searches (
            user_id INTEGER PRIMARY KEY,
            task_ids TEXT NOT NULL,
            query TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
        """)
        
        # Безопасная автомиграция: добавляем колонки, если их еще нет
        async with db.execute("PRAGMA table_info(users);") as cursor:
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]
            if "lang" not in column_names:
                await db.execute("ALTER TABLE users ADD COLUMN lang TEXT DEFAULT 'ru';")
            if "notion_db_id" not in column_names:
                await db.execute("ALTER TABLE users ADD COLUMN notion_db_id TEXT;")
            if "notion_token" not in column_names:
                await db.execute("ALTER TABLE users ADD COLUMN notion_token TEXT;")

        async with db.execute("PRAGMA table_info(tasks);") as cursor:
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]
            if "details" not in column_names:
                await db.execute("ALTER TABLE tasks ADD COLUMN details TEXT;")
            if "duration" not in column_names:
                await db.execute("ALTER TABLE tasks ADD COLUMN duration INTEGER;")
            if "importance" not in column_names:
                await db.execute("ALTER TABLE tasks ADD COLUMN importance TEXT;")
        
        await db.commit()