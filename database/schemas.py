from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from database.models import TaskImportance


class TaskActionSchema(BaseModel):
    action: Literal["create", "update", "delete", "select", "forbidden", "unknown", "add-to-notion"] = Field(
        ...,
        description="Что нужно сделать: создать (create), изменить (update), удалить/завершить (delete), выбрать/найти (select), запрещено (forbidden) или непонятно (unknown), добавить в Notion (add-to-notion)"
    )
    content: Optional[str] = Field(None, description="Короткое название задачи, например 'Встреча с Тинькофф'")
    details: Optional[str] = Field(None, description="Подробное описание, перевод слова или дополнительные примечания к задаче")
    # ИИ отдает дату в текстовом формате, который мы парсим в коде
    time: Optional[str] = Field(None, description="Когда напомнить? Формат YYYY-MM-DD HH:MM. Если время не указано, оставь null")
    task_id: Optional[int] = Field(None, description="ID задачи, если юзер просит изменить или удалить конкретную")
    task_ids: Optional[List[int]] = Field(None, description="Список ID задач, выбранных для действия select")
    duration: Optional[int] = Field(None, description="Ориентировочная продолжительность задачи в минутах")
    importance: Optional[TaskImportance] = Field(None, description="Важность/приоритет задачи: 'low' (низкая), 'medium' (средняя) или 'most important' (высокая/важная). Заполняется, только если пользователь явно указал на важность. По умолчанию null.")


class MultiTaskActionSchema(BaseModel):
    tasks: List[TaskActionSchema] = Field(
        ...,
        description="Список задач/действий, найденных в сообщении пользователя"
    )