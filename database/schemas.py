from pydantic import BaseModel, Field
from typing import Optional, Literal, List


class TaskActionSchema(BaseModel):
    action: Literal["create", "update", "delete", "select", "forbidden", "unknown"] = Field(
        ...,
        description="Что нужно сделать: создать (create), изменить (update), удалить/завершить (delete), выбрать/найти (select), запрещено (forbidden) или непонятно (unknown)"
    )
    content: Optional[str] = Field(None, description="Короткое название задачи, например 'Встреча с Тинькофф'")
    details: Optional[str] = Field(None, description="Подробное описание, перевод слова или дополнительные примечания к задаче")
    # ИИ отдает дату в текстовом формате, который мы парсим в коде
    time: Optional[str] = Field(None, description="Когда напомнить? Формат YYYY-MM-DD HH:MM. Если время не указано, оставь null")
    task_id: Optional[int] = Field(None, description="ID задачи, если юзер просит изменить или удалить конкретную")
    task_ids: Optional[List[int]] = Field(None, description="Список ID задач, выбранных для действия select")
    duration: Optional[int] = Field(None, description="Ориентировочная продолжительность задачи в минутах")


class MultiTaskActionSchema(BaseModel):
    tasks: List[TaskActionSchema] = Field(
        ...,
        description="Список задач/действий, найденных в сообщении пользователя"
    )