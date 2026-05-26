from pydantic import BaseModel, Field
from typing import Optional, Literal

class TaskActionSchema(BaseModel):
    action: Literal["create", "update", "delete", "unknown"] = Field(
        ...,
        description="Что нужно сделать: создать (create), изменить (update), удалить/завершить (delete) или непонятно (unknown)"
    )
    content: Optional[str] = Field(None, description="Короткое название задачи, например 'Встреча с Тинькофф'")
    # В идеале пусть ИИ отдает сразу ISO строку или timestamp, но для начала сойдет и текст даты
    time: Optional[str] = Field(None, description="Когда напомнить? Формат YYYY-MM-DD HH:MM. Если время не указано, оставь null")
    task_id: Optional[int] = Field(None, description="ID задачи, если юзер просит изменить или удалить конкретную")