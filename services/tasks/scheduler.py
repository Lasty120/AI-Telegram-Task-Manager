from datetime import datetime
from aiogram import Bot
from apscheduler.jobstores.base import JobLookupError

from services.scheduler import scheduler, send_task_notification
from config import TIMEZONE
# Проверка задачи без срока — для них не планируем напоминания
from utils.date_utils import is_fallback_timestamp


class SchedulerService:
    """
    Сервис для работы с планировщиком задач (APScheduler).
    Управляет созданием, обновлением и удалением напоминаний о задачах в Telegram.
    """

    def __init__(self, bot: Bot, user):
        """
        Инициализирует сервис планировщика.
        
        Args:
            bot (Bot): Экземпляр бота Telegram для отправки сообщений.
            user: Объект пользователя (Row, dict или int tg_id), для которого планируются напоминания.
        """
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
        """
        Вспомогательный метод для безопасного удаления задачи из планировщика по её ID.
        Не вызывает ошибку, если задача уже была удалена или отсутствует.
        
        Args:
            job_id (str): Уникальный ID задачи в APScheduler.
        """
        try:
            scheduler.remove_job(job_id)
        except JobLookupError:
            # Игнорируем ошибку отсутствия задачи в планировщике
            pass

    def remove_scheduler_jobs(self, task_id: int):
        """
        Удаляет связанные с задачей напоминания из планировщика.
        
        Args:
            task_id (int): Уникальный ID задачи из базы данных.
        """
        self.safe_remove_job(f"task_{task_id}")

    def schedule_or_remove(self, job_id: str, run_date: datetime, notification_func, job_kwargs: dict):
        """
        Добавляет задачу в планировщик, если время её выполнения находится в будущем.
        Если время уже прошло, удаляет задачу с данным ID.
        
        Args:
            job_id (str): Уникальный ID задачи в APScheduler.
            run_date (datetime): Время выполнения напоминания.
            notification_func (callable): Асинхронная функция для отправки уведомления.
            job_kwargs (dict): Аргументы, передаваемые в notification_func.
        """
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
        duration: int | None,
        importance: str | None = None
    ):
        """
        Добавляет или обновляет задачу напоминания в планировщике.
        Если время задачи уже в прошлом, удаляет её из планировщика.
        Если задача без срока (FALLBACK 2060), напоминание не ставится.
        
        Args:
            task_id (int): Уникальный ID задачи.
            content (str): Название/текст задачи.
            details (str | None): Детальное описание.
            localized_dt (datetime): Локализованное время начала задачи.
            duration (int | None): Продолжительность задачи в минутах.
            importance (str | None): Важность задачи.
        """
        # Не планируем напоминание для задач без срока (метка 2060)
        task_ts = int(localized_dt.timestamp())
        if is_fallback_timestamp(task_ts):
            # Удаляем возможное устаревшее напоминание, если оно было
            self.safe_remove_job(f"task_{task_id}")
            return

        job_kwargs = {
            'bot': self.bot,
            'user_id': self.tg_id,
            'task_text': content,
            'task_details': details,
            'task_id': task_id,
            'task_importance': importance
        }

        self.schedule_or_remove(
            job_id=f"task_{task_id}",
            run_date=localized_dt,
            notification_func=send_task_notification,
            job_kwargs=job_kwargs
        )
