-- Миграция 001: начальная схема базы данных.
--
-- Перенесена из database/init_db.py (SQLite) на PostgreSQL:
--   * SERIAL/INTEGER PRIMARY KEY -> BIGSERIAL
--   * tg_id INTEGER -> BIGINT (Telegram ID не помещается в 32-битный INTEGER)
--   * PRAGMA убраны — в PostgreSQL они не нужны
--   * учтены все колонки, которые в SQLite-версии добавлялись отдельными
--     ALTER TABLE через "безопасную автомиграцию" — здесь они сразу
--     присутствуют в основной схеме

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    tg_id BIGINT UNIQUE NOT NULL,
    lang TEXT NOT NULL DEFAULT 'ru',
    notion_db_id TEXT,
    notion_token TEXT,
    notion_status_completed TEXT,
    notion_status_created TEXT,
    notion_status_modified TEXT,
    notion_status_notified TEXT,
    notion_statuses TEXT,
    notion_multi_selects TEXT,
    notion_user_id TEXT,
    notion_user_name TEXT,
    pending_notion_user_id TEXT,
    pending_notion_user_name TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    details TEXT,
    status INTEGER NOT NULL DEFAULT 0,
    time BIGINT NOT NULL,
    user_id BIGINT NOT NULL REFERENCES users (id),
    duration INTEGER,
    importance TEXT,
    notion_status TEXT,
    notion_multi_select TEXT,
    notion_added INTEGER NOT NULL DEFAULT 0,
    notion_page_id TEXT
);

-- Кэш последних результатов поиска (выбора) пользователя для пагинации
CREATE TABLE IF NOT EXISTS user_searches (
    user_id BIGINT PRIMARY KEY REFERENCES users (id),
    task_ids TEXT NOT NULL,
    query TEXT
);

-- Кэш участников рабочего пространства Notion
CREATE TABLE IF NOT EXISTS notion_workspace_users (
    id BIGSERIAL PRIMARY KEY,
    tg_id BIGINT NOT NULL REFERENCES users (tg_id) ON DELETE CASCADE,
    notion_user_id TEXT NOT NULL,
    name TEXT,
    email TEXT,
    UNIQUE (tg_id, notion_user_id)
);
