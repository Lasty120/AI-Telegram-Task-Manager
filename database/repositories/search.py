"""
Репозиторий кэша поисковых запросов.

Хранит последний результат поиска пользователя (список id задач + строка запроса)
для постраничной навигации по результатам без повторного запроса к ИИ.
"""

from database.repositories.base import BaseRepository, DbConnection


class SearchRepository(BaseRepository):
    """
    Операции над таблицей user_searches.

    Таблица хранит по одной записи на пользователя (upsert по user_id).
    task_ids сохраняются как строка через запятую (совместимо с текущей схемой).
    """

    def __init__(self, db: DbConnection) -> None:
        super().__init__(db)

    async def save(self, user_id: int, task_ids: list[int], query: str) -> None:
        """
        Сохраняет (или обновляет) кэш поискового запроса пользователя.

        ON CONFLICT DO UPDATE — upsert: одна операция вместо INSERT + UPDATE.
        task_ids сериализуются в строку «1,2,3» для хранения в text-колонке.
        """
        task_ids_str = ",".join(map(str, task_ids))
        await self.db.execute(
            """
            INSERT INTO user_searches (user_id, task_ids, query)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO UPDATE
                SET task_ids = EXCLUDED.task_ids,
                    query    = EXCLUDED.query
            """,
            user_id, task_ids_str, query,
        )

    async def get(self, user_id: int) -> dict | None:
        """
        Возвращает кэшированный поисковый запрос или None.

        Десериализует task_ids обратно в list[int].
        """
        row = await self.db.fetchrow(
            "SELECT task_ids, query FROM user_searches WHERE user_id = $1",
            user_id,
        )
        if not row:
            return None

        task_ids = [int(x) for x in row["task_ids"].split(",") if x]
        return {"task_ids": task_ids, "query": row["query"]}
