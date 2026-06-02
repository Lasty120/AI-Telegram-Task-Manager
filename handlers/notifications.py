from datetime import datetime, timedelta
import pytz

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiosqlite import Connection, Row

from database.crud.task import complete_task, get_task_by_id, update_task
from messages import TaskMessages
from services.scheduler import scheduler, send_task_notification

router = Router()


@router.callback_query(F.data.startswith("complete_task:"))
async def complete_task_callback(callback: CallbackQuery, db: Connection, user: Row):
    task_id = int(callback.data.split(":")[1])
    task = await get_task_by_id(db, task_id)
    if not task:
        await callback.message.edit(TaskMessages.TASK_DELETE_ID_MISSING, show_alert=True)
        return

    if task['user_id'] != user['id']:
        await callback.answer(TaskMessages.TASK_DELETE_ACCESS_DENIED, show_alert=True)
        return

    await complete_task(db, task_id)

    # Попытка удалить задачу из планировщика, если она там осталась
    try:
        scheduler.remove_job(f"task_{task_id}")
    except Exception:
        pass

    await callback.answer()



    await callback.message.edit_text(
        text=TaskMessages.task_completed(task['content']),
        parse_mode="Markdown",
        reply_markup=None
    )


@router.callback_query(F.data.startswith("delay_task:"))
async def delay_task_callback(callback: CallbackQuery, db: Connection, user: Row):
    task_id = int(callback.data.split(":")[1])
    task = await get_task_by_id(db, task_id)
    if not task:
        await callback.answer(TaskMessages.TASK_NOT_FOUND, show_alert=True)
        return

    if task['user_id'] != user['id']:
        await callback.answer(TaskMessages.TASK_UPDATE_ACCESS_DENIED, show_alert=True)
        return

    minutes = 15
    tz = pytz.timezone("Asia/Almaty")
    now = datetime.now(tz)
    new_time_dt = now + timedelta(minutes=minutes)
    new_time_timestamp = int(new_time_dt.timestamp())

    # Обновляем время в базе данных
    await update_task(
        db=db,
        task_id=task_id,
        time_val=new_time_timestamp
    )

    # Перепланируем отправку уведомления
    scheduler.add_job(
        send_task_notification,
        trigger='date',
        run_date=new_time_dt,
        kwargs={
            'bot': callback.message.bot,
            'user_id': user['tg_id'],
            'task_text': task['content'],
            'task_details': task['details'],
            'task_id': task_id
        },
        id=f"task_{task_id}",
        replace_existing=True
    )

    await callback.answer()

    # Обновляем сообщение в чате
    text = TaskMessages.task_notification(task['content'], task['details'])
    text += TaskMessages.task_delay(new_time_dt.strftime('%H:%M'))

    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=None
    )
