from aiogram import Router

from.tasks import router as task_router
from.tasks_ai import router as task_ai_router


def get_handlers_router() -> Router:
    router = Router()

    # Объединяем их здесь, внутри папки handlers
    router.include_router(task_router)
    router.include_router(task_ai_router)

    return router