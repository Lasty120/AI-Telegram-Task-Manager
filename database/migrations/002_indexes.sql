-- Миграция 002: индексы для ускорения выборок задач по пользователю.
--
-- (user_id, status) — для запросов вида "активные/выполненные задачи пользователя"
-- (user_id, time)   — для запросов вида "задачи пользователя, отсортированные по времени"
--                      (используется планировщиком напоминаний и due_tasks)

CREATE INDEX IF NOT EXISTS idx_tasks_user_id_status ON tasks (user_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_user_id_time ON tasks (user_id, time);
