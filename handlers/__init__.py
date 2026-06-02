from aiogram import Router

from handlers.start import router as start_router
from handlers.tasks import router as task_router
from handlers.tasks_ai import router as task_ai_router
from handlers.voice_transcriptor import router as voice_transcriptor_router


def get_handlers_router() -> Router:
    router = Router()

    # Объединяем их здесь, внутри папки handlers
    router.include_router(start_router)
    router.include_router(task_router)
    router.include_router(task_ai_router)
    router.include_router(voice_transcriptor_router)

    return router