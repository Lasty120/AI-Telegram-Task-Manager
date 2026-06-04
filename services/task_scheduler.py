from datetime import datetime, timedelta
from aiogram import Bot
from apscheduler.jobstores.base import JobLookupError

from services.scheduler import scheduler, send_task_notification, send_task_end_notification
from config import TIMEZONE


class TaskSchedulerService:
    def __init__(self, bot: Bot, user):
        self.bot = bot
        self.tz = TIMEZONE
        
        # Разрешаем извлечение tg_id из Row, dict или используем переданное значение напрямую
        if isinstance(user, int):
            self.tg_id = user
        elif hasattr(user, 'keys') and 'tg_id' in user.keys():
            self.tg_id = user['tg_id']
        elif isinstance(user, dict) and 'tg_id' in user:
            self.tg_id = user['tg_id']
        else:
            self.tg_id = getattr(user, 'tg_id', user)

    @staticmethod
    def safe_remove_job(job_id: str):
        """Вспомогательный метод для безопасного удаления задачи по ID без глушения системных ошибок."""
        try:
            scheduler.remove_job(job_id)
        except JobLookupError:
            # Игнорируем ТОЛЬКО ошибку того, что задача не найдена в планировщике
            pass

    def remove_scheduler_jobs(self, task_id: int):
        """Удаляет связанные работы из планировщика."""
        self.safe_remove_job(f"task_{task_id}")
        self.safe_remove_job(f"task_end_{task_id}")

    def schedule_or_remove(self, job_id: str, run_date: datetime, notification_func, job_kwargs: dict):
        now = datetime.now(self.tz)
        if run_date > now:
            scheduler.add_job(
                notification_func,
                trigger='date',
                run_date=run_date,
                kwargs=job_kwargs,
                id=job_id,
                replace_existing=True
            )
        else:
            self.safe_remove_job(job_id)

    def update_scheduler_jobs(
        self,
        task_id: int,
        content: str,
        details: str | None,
        localized_dt: datetime,
        duration: int | None
    ):
        """
        Добавляет/обновляет задачи старта и завершения в планировщике.
        Если время в прошлом, удаляет соответствующие работы.
        """
        job_kwargs = {
            'bot': self.bot,
            'user_id': self.tg_id,
            'task_text': content,
            'task_details': details,
            'task_id': task_id
        }

        self.schedule_or_remove(
            job_id=f"task_{task_id}",
            run_date=localized_dt,
            notification_func=send_task_notification,
            job_kwargs=job_kwargs
        )

        # 2. Задача на завершение
        if duration and duration > 0:
            task_end_time = localized_dt + timedelta(minutes=duration)
            self.schedule_or_remove(
                job_id=f"task_end_{task_id}",
                run_date=task_end_time,
                notification_func=send_task_end_notification,
                job_kwargs=job_kwargs
            )
        else:
            self.safe_remove_job(f"task_end_{task_id}")
