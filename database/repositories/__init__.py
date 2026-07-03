"""
Пакет репозиториев — единая точка импорта.

Использование в хендлерах и сервисах:

    from database.repositories import TaskRepository, UserRepository

Каждый репозиторий принимает asyncpg.Connection и инкапсулирует
все SQL-операции над своей таблицей.
"""

from database.repositories.base import BaseRepository, DbConnection
from database.repositories.task import TaskRepository
from database.repositories.user import UserRepository
from database.repositories.search import SearchRepository
from database.repositories.notion_users import NotionWorkspaceRepository

__all__ = [
    "BaseRepository",
    "DbConnection",
    "TaskRepository",
    "UserRepository",
    "SearchRepository",
    "NotionWorkspaceRepository",
]
