from pydantic import BaseModel, Field
from typing import Optional, Literal, List


class TaskActionSchema(BaseModel):
    action: Literal["create", "update", "delete", "unknown"] = Field(
        ...,
        description="Что нужно сделать: создать (create), изменить (update), удалить/завершить (delete) или непонятно (unknown)"
    )
    content: Optional[str] = Field(None, description="Короткое название задачи, например 'Встреча с Тинькофф'")
    # ИИ отдает дату в текстовом формате, который мы парсим в коде
    time: Optional[str] = Field(None, description="Когда напомнить? Формат YYYY-MM-DD HH:MM. Если время не указано, оставь null")
    task_id: Optional[int] = Field(None, description="ID задачи, если юзер просит изменить или удалить конкретную")


class MultiTaskActionSchema(BaseModel):
    tasks: List[TaskActionSchema] = Field(
        ...,
        description="Список задач/действий, найденных в сообщении пользователя"
    )