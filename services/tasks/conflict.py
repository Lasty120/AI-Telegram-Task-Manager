from datetime import datetime

from config import TIMEZONE
from database.repositories import TaskRepository
from messages import TaskMessages
from services.tasks.scheduler import SchedulerService
from services.tasks.notion_sync import NotionSyncService


class ConflictService:
    """
    Сервис для проверки и разрешения временных конфликтов между задачами пользователя.
    Помогает находить свободное время для задач и автоматически сдвигать задачи при коллизиях.
    """

    def __init__(
        self,
        task_repo: TaskRepository,
        user: dict,
        scheduler_service: SchedulerService,
        notion_service: NotionSyncService | None = None,
    ):
        """
        Инициализирует сервис конфликтов.

        Args:
            task_repo (TaskRepository): Репозиторий задач (asyncpg).
            user (dict): Словарь пользователя из БД.
            scheduler_service (SchedulerService): Сервис для обновления напоминаний.
            notion_service (NotionSyncService | None): Сервис для синхронизации с Notion.
        """
        self.task_repo = task_repo
        self.user = user
        self.scheduler_service = scheduler_service
        self.notion_service = notion_service
        self.tz = TIMEZONE

    async def find_first_free_slot(self, duration_mins: int, exclude_task_id: int | None = None) -> datetime:
        """
        Ищет ближайший свободный временной слот для задачи заданной длительности (в минутах),
        начиная с текущего момента времени. Слот не должен пересекаться с существующими задачами.

        Args:
            duration_mins (int): Длительность новой задачи в минутах.
            exclude_task_id (int | None): ID задачи, которую нужно исключить из проверки
                                          пересечений (например, сдвигаемая задача).

        Returns:
            datetime: Локализованный datetime начала найденного свободного слота.
        """
        if not duration_mins:
            duration_mins = 30

        # Получаем все активные задачи пользователя через репозиторий
        active_tasks = await self.task_repo.get_active(user_id=self.user["id"])

        now = datetime.now(self.tz)
        candidate_start = now.replace(second=0, microsecond=0)

        # Строим список интервалов существующих задач
        intervals = []
        for task in active_tasks:
            if exclude_task_id and task["id"] == exclude_task_id:
                continue
            task_start = task["time"]
            task_dur = task.get("duration") or 30
            task_end = task_start + task_dur * 60
            intervals.append((task_start, task_end))

        # Сортируем интервалы по времени начала для эффективного поиска
        intervals.sort(key=lambda x: x[0])

        # Ищем свободный промежуток методом перебора с смещением
        while True:
            candidate_start_ts = int(candidate_start.timestamp())
            candidate_end_ts = candidate_start_ts + duration_mins * 60

            overlap = False
            for start, end in intervals:
                # Если кандидат пересекает текущий занятый слот
                if candidate_start_ts < end and candidate_end_ts > start:
                    overlap = True
                    # Смещаем кандидата на время окончания конфликтующей задачи
                    candidate_start = datetime.fromtimestamp(end, self.tz)
                    break

            if not overlap:
                return candidate_start

    async def check_conflict(
        self,
        start_ts: int,
        duration_mins: int,
        exclude_task_id: int | None = None,
    ) -> dict | None:
        """
        Проверяет, пересекается ли временной интервал новой задачи с существующими активными задачами.

        Args:
            start_ts (int): Время начала проверяемого интервала (Unix timestamp).
            duration_mins (int): Продолжительность задачи в минутах.
            exclude_task_id (int | None): ID задачи, которую не нужно учитывать при поиске.

        Returns:
            dict | None: Первая конфликтующая задача или None, если конфликт отсутствует.
        """
        if not duration_mins:
            duration_mins = 30

        # Получаем активные задачи пользователя через репозиторий
        active_tasks = await self.task_repo.get_active(user_id=self.user["id"])
        end_ts = start_ts + duration_mins * 60

        for task in active_tasks:
            if exclude_task_id and task["id"] == exclude_task_id:
                continue
            task_start = task["time"]
            task_dur = task.get("duration") or 30
            task_end = task_start + task_dur * 60

            # Условие пересечения временных интервалов
            if start_ts < task_end and end_ts > task_start:
                return task

        return None

    async def resolve_conflict(
        self,
        action: str,
        new_task_id: int | None = None,
        old_task_id: int | None = None,
        add_to_notion: bool = False,
    ) -> str:
        """
        Разрешает конфликт между новой и старой задачами на основе выбора пользователя.

        Действия:
        - "ignore"   — оставить обе задачи без изменений.
        - "move_old" — сдвинуть старую задачу на ближайший свободный слот.
        - "move_new" — сдвинуть новую задачу на ближайший свободный слот.

        Args:
            action (str): Выбранное действие ("ignore", "move_old", "move_new").
            new_task_id (int | None): ID новой задачи.
            old_task_id (int | None): ID старой задачи.
            add_to_notion (bool): Флаг добавления новой задачи в Notion.

        Returns:
            str: Текст ответа для пользователя.
        """
        # 1. Быстрый выход при игнорировании конфликта
        if action == "ignore":
            if add_to_notion and self.notion_service and new_task_id:
                new_task = await self.task_repo.get_by_id(new_task_id)
                if new_task:
                    await self.notion_service.add_single_task_to_notion(new_task)
            return TaskMessages.conflict_ignore()

        # 2. Загружаем обе задачи из репозитория для проверки существования
        new_task = await self.task_repo.get_by_id(new_task_id)
        old_task = await self.task_repo.get_by_id(old_task_id)

        if not new_task or not old_task:
            return TaskMessages.conflict_task_not_found()

        new_duration = new_task.get("duration") or 30
        old_duration = old_task.get("duration") or 30

        # 3. Определяем, какую из задач нужно сдвинуть
        if action == "move_old":
            target_id, target_task, target_dur = old_task_id, old_task, old_duration
        else:  # move_new
            target_id, target_task, target_dur = new_task_id, new_task, new_duration

        # 4. Находим первый свободный слот для перемещаемой задачи
        new_dt = await self.find_first_free_slot(target_dur, exclude_task_id=target_id)
        new_ts = int(new_dt.timestamp())

        # 5. Обновляем время задачи в репозитории и перепланируем напоминание
        await self.task_repo.update(target_id, time=new_ts)
        self.scheduler_service.update_scheduler_jobs(
            task_id=target_id,
            content=target_task["content"],
            details=target_task.get("details"),
            localized_dt=new_dt,
            duration=target_dur,
            importance=target_task.get("importance"),
        )

        # 6. Синхронизируем новую задачу с Notion при необходимости
        if add_to_notion and self.notion_service and new_task_id:
            # Получаем актуальный объект новой задачи (на случай если сдвинули её время)
            updated_new_task = await self.task_repo.get_by_id(new_task_id)
            if updated_new_task:
                await self.notion_service.add_single_task_to_notion(updated_new_task)

        # 7. Формируем сообщение о результате разрешения коллизии
        new_dt_str = new_dt.strftime("%Y-%m-%d %H:%M")

        if action == "move_old":
            display_new_time = datetime.fromtimestamp(new_task["time"], self.tz).strftime("%Y-%m-%d %H:%M")
            return TaskMessages.conflict_resolved_move_old(
                new_title=new_task["content"],
                new_time=display_new_time,
                old_title=old_task["content"],
                old_new_time=new_dt_str,
            )
        else:
            display_old_time = datetime.fromtimestamp(old_task["time"], self.tz).strftime("%Y-%m-%d %H:%M")
            return TaskMessages.conflict_resolved_move_new(
                new_title=new_task["content"],
                new_time=new_dt_str,
                old_title=old_task["content"],
                old_time=display_old_time,
            )