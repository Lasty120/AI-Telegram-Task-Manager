import re
import aiohttp
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from aiosqlite import Connection

from database.crud.user import update_user_notion
from keyboards.reply_keyboards import get_registration_kb, get_main_kb
from messages import NotionMessages

router = Router()

class NotionRegistrationStates(StatesGroup):
    waiting_for_token = State()
    waiting_for_db_id = State()


def extract_db_id(text: str) -> str | None:
    # Ищет 32-символьный хекс-код (с опциональными дефисами)
    match = re.search(r'([a-fA-F0-9]{8}-?[a-fA-F0-9]{4}-?[a-fA-F0-9]{4}-?[a-fA-F0-9]{4}-?[a-fA-F0-9]{12}|[a-fA-F0-9]{32})', text)
    if match:
        return match.group(1).replace('-', '')
    return None


async def validate_notion(token: str | None, db_id: str | None) -> tuple[bool, str | None]:
    if not token:
        if db_id:
            return False, "Token is missing but Database ID is provided."
        return True, None

    if db_id:
        url = f"https://api.notion.com/v1/databases/{db_id}"
    else:
        url = "https://api.notion.com/v1/users/me"

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return True, None
                else:
                    try:
                        err_data = await response.json()
                        err_msg = err_data.get("message", f"HTTP {response.status}")
                    except Exception:
                        err_msg = f"HTTP {response.status}"
                    return False, err_msg
    except Exception as e:
        return False, str(e)


# Отмена регистрации на любом шаге FSM
@router.message(StateFilter(NotionRegistrationStates.waiting_for_token, NotionRegistrationStates.waiting_for_db_id), F.text.in_({"Отмена", "Cancel", "/cancel"}))
async def cmd_cancel_registration(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        text=NotionMessages.registration_cancelled(),
        reply_markup=get_main_kb()
    )


# Начало регистрации
@router.message(Command("start_registration"))
async def cmd_start_registration(message: Message, state: FSMContext):
    await state.set_state(NotionRegistrationStates.waiting_for_token)
    await message.answer(
        text=NotionMessages.start_registration(),
        reply_markup=get_registration_kb(),
        parse_mode="HTML",
        disable_web_page_preview=True
    )


# Шаг 1: Получение токена
@router.message(NotionRegistrationStates.waiting_for_token)
async def process_token(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""

    # Пропуск шага
    if text in {"Пропустить", "Skip", "/skip"}:
        await state.update_data(token=None)
        await state.set_state(NotionRegistrationStates.waiting_for_db_id)
        await message.answer(
            text=NotionMessages.ask_db_id(),
            reply_markup=get_registration_kb(),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        return

    # Локальная валидация формата токена
    if not text.startswith("ntn_"):
        await message.answer(
            text=NotionMessages.invalid_token(),
            reply_markup=get_registration_kb(),
            parse_mode="HTML"
        )
        return

    await state.update_data(token=text)
    await state.set_state(NotionRegistrationStates.waiting_for_db_id)
    await message.answer(
        text=NotionMessages.ask_db_id(),
        reply_markup=get_registration_kb(),
        parse_mode="HTML",
        disable_web_page_preview=True
    )


# Шаг 2: Получение ID базы данных и завершение
@router.message(NotionRegistrationStates.waiting_for_db_id)
async def process_db_id(message: Message, state: FSMContext, db: Connection):
    text = message.text.strip() if message.text else ""
    user_data = await state.get_data()
    token = user_data.get("token")

    # Пропуск шага
    if text in {"Пропустить", "Skip", "/skip"}:
        db_id = None
    else:
        # Извлечение ID базы данных
        db_id = extract_db_id(text)
        if not db_id:
            await message.answer(
                text=NotionMessages.invalid_db_id(),
                reply_markup=get_registration_kb(),
                parse_mode="HTML"
            )
            return

    # Информируем пользователя о проверке
    check_msg = await message.answer(
        text=NotionMessages.verifying_connection(),
        parse_mode="HTML"
    )

    # Валидация соединения с Notion
    success, err_msg = await validate_notion(token, db_id)

    if not success:
        # Удаляем сообщение о проверке
        try:
            await check_msg.delete()
        except Exception:
            pass

        # Если не удалось соединиться, сообщаем и просим начать сначала (с шага отправки токена)
        await state.set_state(NotionRegistrationStates.waiting_for_token)
        await message.answer(
            text=NotionMessages.connection_failed(err_msg or "Unknown error"),
            reply_markup=get_registration_kb(),
            parse_mode="HTML"
        )
        return

    # Удаляем сообщение о проверке
    try:
        await check_msg.delete()
    except Exception:
        pass

    # Сохранение в базу данных
    await update_user_notion(
        db=db,
        tg_id=message.from_user.id,
        notion_token=token,
        notion_db_id=db_id
    )

    await state.clear()
    await message.answer(
        text=NotionMessages.registration_success(token, db_id),
        reply_markup=get_main_kb(),
        parse_mode="HTML"
    )
