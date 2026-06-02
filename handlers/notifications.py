from datetime import datetime, timedelta
import pytz

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiosqlite import Connection, Row

from database.crud.task import complete_task, get_task_by_id, update_task
from messages import TaskMessages
from services.scheduler import scheduler, send_task_notification, send_task_end_notification

router = Router()


@router.callback_query(F.data.startswith("complete_task:"))
async def complete_task_callback(callback: CallbackQuery, db: Connection, user: Row):
    task_id = int(callback.data.split(":")[1])
    task = await get_task_by_id(db, task_id)
    if not task:
        await callback.answer(TaskMessages.TASK_NOT_FOUND, show_alert=True)
        return

    if task['user_id'] != user['id']:
        await callback.answer(TaskMessages.TASK_UPDATE_ACCESS_DENIED, show_alert=True)
        return

    await complete_task(db, task_id)

    # Попытка удалить задачу из планировщика, если она там осталась
    try:
        scheduler.remove_job(f"task_{task_id}")
    except Exception:
        pass
    try:
        scheduler.remove_job(f"task_end_{task_id}")
    except Exception:
        pass

    await callback.answer(TaskMessages.TASK_COMPLETED_SUCCESS)

    # Обновляем текст сообщения, убирая кнопки
    text = TaskMessages.task_notification(task['content'], task['details'])
    text += "\n\n✅ <b>Выполнено</b>"

    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
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

    tz = pytz.timezone("Asia/Almaty")
    now = datetime.now(tz)
    new_time_dt = now + timedelta(minutes=15)
    new_time_timestamp = int(new_time_dt.timestamp())

    # Обновляем время в базе данных
    await update_task(
        db=db,
        task_id=task_id,
        time_val=new_time_timestamp
    )

    # Перепланируем отправку уведомления о начале
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

    # Если есть длительность, перепланируем уведомление о завершении
    task_dur = task['duration'] if 'duration' in task.keys() and task['duration'] else 0
    if task_dur > 0:
        new_end_dt = new_time_dt + timedelta(minutes=task_dur)
        scheduler.add_job(
            send_task_end_notification,
            trigger='date',
            run_date=new_end_dt,
            kwargs={
                'bot': callback.message.bot,
                'user_id': user['tg_id'],
                'task_text': task['content'],
                'task_details': task['details'],
                'task_id': task_id
            },
            id=f"task_end_{task_id}",
            replace_existing=True
        )
    else:
        try:
            scheduler.remove_job(f"task_end_{task_id}")
        except Exception:
            pass

    await callback.answer(TaskMessages.TASK_DELAYED_SUCCESS)

    # Обновляем сообщение в чате
    text = TaskMessages.task_notification(task['content'], task['details'])
    text += f"\n\n⏰ <b>Отложено на 15 минут</b> (до {new_time_dt.strftime('%H:%M')})"

    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=None
    )
