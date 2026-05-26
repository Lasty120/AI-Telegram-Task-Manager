from aiogram import Router

from.tasks import router as task_router


def get_handlers_router() -> Router:
    router = Router()

    # Объединяем их здесь, внутри папки handlers
    router.include_router(task_router)

    return router