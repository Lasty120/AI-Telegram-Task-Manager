import re
from aiogram import Router, F, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiosqlite import Connection
import logging

from database.crud.user import (
    update_user_notion, 
    update_user_pending_notion,
    clear_notion_workspace_users,
    save_notion_workspace_users,
    get_cached_notion_users
)
from keyboards.reply_keyboards import get_registration_kb, get_main_kb, get_cancel_kb
from keyboards.inline_keyboards import (
    get_status_selection_keyboard, 
    get_notion_users_keyboard, 
    get_admin_approval_keyboard,
    get_notion_data_sources_keyboard
)
from services.notion import NotionClient
from services.notion.service import (
    get_notion_workspace_users,
    discover_notion_data_sources
)
from messages import NotionMessages
from config import ADMIN_IDS
from handlers.states import NotionRegistrationStates

router = Router()


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
        # Используем новый метод обнаружения источников данных для валидации
        type_found, data_sources, err_msg = await discover_notion_data_sources(token, db_id)
        if type_found:
            return True, None
        return False, err_msg
    else:
        client = NotionClient(token)
        try:
            response = await client.get("/v1/users/me")
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



async def initiate_user_selection(
    message_or_callback,
    state: FSMContext,
    token: str,
    db_id: str | None,
    db: Connection,
    db_name: str | None = None
):
    """
    Получает пользователей из Notion и переводит FSM в режим выбора пользователя.
    """
    if isinstance(message_or_callback, CallbackQuery):
        msg = await message_or_callback.message.answer(
            text=NotionMessages.notion_users_loading(),
            parse_mode="HTML"
        )
        tg_id = message_or_callback.from_user.id
    else:
        msg = await message_or_callback.answer(
            text=NotionMessages.notion_users_loading(),
            parse_mode="HTML"
        )
        tg_id = message_or_callback.from_user.id

    # Получаем список участников из Notion с пагинацией
    notion_users = await get_notion_workspace_users(token)

    try:
        await msg.delete()
    except Exception:
        pass

    if not notion_users:
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.answer(
                text=NotionMessages.notion_users_empty(),
                parse_mode="HTML",
                reply_markup=get_main_kb()
            )
        else:
            await message_or_callback.answer(
                text=NotionMessages.notion_users_empty(),
                parse_mode="HTML",
                reply_markup=get_main_kb()
            )
        await state.clear()
        return

    # Сохраняем участников Notion в кэш БД для этого Telegram-пользователя
    await clear_notion_workspace_users(db, tg_id)
    await save_notion_workspace_users(db, tg_id, notion_users)

    # Инициализируем пустой список для результатов поиска в FSM state
    await state.update_data(
        token=token,
        db_id=db_id,
        db_name=db_name,
        notion_users=[]
    )
    await state.set_state(NotionRegistrationStates.waiting_for_user_selection)

    kb = get_cancel_kb()
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.answer(
            text=NotionMessages.notion_users_loaded_search_prompt(),
            reply_markup=kb,
            parse_mode="HTML"
        )
    else:
        await message_or_callback.answer(
            text=NotionMessages.notion_users_loaded_search_prompt(),
            reply_markup=kb,
            parse_mode="HTML"
        )


# Отмена регистрации на любом шаге FSM
@router.message(StateFilter(
    NotionRegistrationStates.waiting_for_token, 
    NotionRegistrationStates.waiting_for_db_id, 
    NotionRegistrationStates.waiting_for_data_source,
    NotionRegistrationStates.waiting_for_created_status, 
    NotionRegistrationStates.waiting_for_completed_status, 
    NotionRegistrationStates.waiting_for_user_selection
), F.text.in_({"Отмена", "Cancel", "/cancel"}))
async def cmd_cancel_registration(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        text=NotionMessages.registration_cancelled(),
        reply_markup=get_main_kb()
    )


# Начало регистрации
@router.message(Command("add_notion"))
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


# Шаг 2: Получение ID базы данных и переход к выбору участника Notion
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

    data_sources = []
    # Валидация соединения с Notion
    if token and db_id:
        type_found, data_sources, err_msg = await discover_notion_data_sources(token, db_id)
        if not type_found:
            try:
                await check_msg.delete()
            except Exception:
                pass
            await state.set_state(NotionRegistrationStates.waiting_for_token)
            await message.answer(
                text=NotionMessages.connection_failed(err_msg or "Unknown error"),
                reply_markup=get_registration_kb(),
                parse_mode="HTML"
            )
            return
    else:
        success, err_msg = await validate_notion(token, db_id)
        if not success:
            try:
                await check_msg.delete()
            except Exception:
                pass
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

    if db_id and token:
        if not data_sources:
            await message.answer(
                text=NotionMessages.no_data_sources_found(),
                reply_markup=get_main_kb(),
                parse_mode="HTML"
            )
            await state.clear()
            return
        elif len(data_sources) == 1:
            # Если ровно 1 источник данных, выбираем его автоматически и переходим к выбору пользователя
            selected_ds = data_sources[0]
            await initiate_user_selection(
                message_or_callback=message,
                state=state,
                token=token,
                db_id=selected_ds["id"],
                db=db,
                db_name=selected_ds["name"]
            )
        else:
            # Если источников несколько, предлагаем выбор
            await state.update_data(
                token=token,
                data_sources=data_sources
            )
            await state.set_state(NotionRegistrationStates.waiting_for_data_source)
            await message.answer(
                text=NotionMessages.ask_data_source(),
                reply_markup=get_notion_data_sources_keyboard(data_sources),
                parse_mode="HTML"
            )
    else:
        # Если пропустили базу данных
        if token:
            await initiate_user_selection(message, state, token, db_id, db=db)
        else:
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


# Шаг 2.5: Обработка выбора источника данных (кнопка)
@router.callback_query(NotionRegistrationStates.waiting_for_data_source, F.data.startswith("select_data_source:"))
async def process_data_source_callback(callback: CallbackQuery, state: FSMContext, db: Connection):
    data = await state.get_data()
    data_sources = data.get("data_sources", [])
    try:
        idx = int(callback.data.split(":")[1])
        selected_ds = data_sources[idx]
    except (IndexError, ValueError):
        await callback.answer()
        return

    token = data.get("token")

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.answer()

    # Сообщаем пользователю о выборе источника данных
    await callback.message.answer(
        text=NotionMessages.data_source_selected(selected_ds["name"]),
        parse_mode="HTML"
    )

    await initiate_user_selection(
        message_or_callback=callback,
        state=state,
        token=token,
        db_id=selected_ds["id"],
        db=db,
        db_name=selected_ds["name"]
    )


# Шаг 2.5: Обработка некорректного текстового ввода на шаге выбора источника данных
@router.message(NotionRegistrationStates.waiting_for_data_source)
async def process_data_source_text(message: Message, state: FSMContext, db: Connection):
    text = message.text.strip() if message.text else ""
    data = await state.get_data()
    data_sources = data.get("data_sources", [])
    token = data.get("token")

    matched = next((ds for ds in data_sources if ds["name"].lower() == text.lower()), None)
    if matched:
        await message.answer(
            text=NotionMessages.data_source_selected(matched["name"]),
            parse_mode="HTML"
        )
        await initiate_user_selection(
            message_or_callback=message,
            state=state,
            token=token,
            db_id=matched["id"],
            db=db,
            db_name=matched["name"]
        )
    else:
        await message.answer(
            text=NotionMessages.ask_data_source(),
            reply_markup=get_notion_data_sources_keyboard(data_sources),
            parse_mode="HTML"
        )


# Обработка выбора пользователя Notion (кнопка)
@router.callback_query(NotionRegistrationStates.waiting_for_user_selection, F.data.startswith("select_notion_user:"))
async def process_notion_user_callback(callback: CallbackQuery, state: FSMContext, db: Connection, bot: Bot):
    data = await state.get_data()
    users = data.get("notion_users", [])
    try:
        idx = int(callback.data.split(":")[1])
        selected_user = users[idx]
    except (IndexError, ValueError):
        await callback.answer()
        return

    token = data.get("token")
    db_id = data.get("db_id")

    # Считываем доступные свойства БД из Notion для кэширования в БД
    from services.notion.service import get_notion_properties_options
    import json
    
    props = await get_notion_properties_options(token, db_id)
    status_options = props.get("statuses") or []
    multi_select_options = props.get("multi_selects") or []

    await state.update_data(
        selected_user_id=selected_user["id"],
        selected_user_name=selected_user["name"],
        status_options=status_options,
        multi_select_options=multi_select_options
    )

    await callback.answer()

    if status_options:
        # Переходим к выбору статуса при создании задачи
        await state.set_state(NotionRegistrationStates.waiting_for_created_status)
        await callback.message.edit_text(
            text=NotionMessages.ask_created_status(),
            reply_markup=get_status_selection_keyboard(status_options),
            parse_mode="HTML"
        )
    else:
        # Сохраняем без статусов, отправляем на одобрение
        await update_user_notion(
            db=db,
            tg_id=callback.from_user.id,
            notion_token=token,
            notion_db_id=db_id,
            notion_status_created=None,
            notion_status_completed=None,
            notion_statuses=json.dumps([]),
            notion_multi_selects=json.dumps(multi_select_options, ensure_ascii=False)
        )
        await update_user_pending_notion(
            db=db,
            tg_id=callback.from_user.id,
            pending_id=selected_user["id"],
            pending_name=selected_user["name"]
        )
        await state.clear()
        await callback.message.edit_text(
            text=NotionMessages.notion_user_approval_pending(),
            parse_mode="HTML"
        )

        # Уведомляем администраторов
        admin_markup = get_admin_approval_keyboard(callback.from_user.id)
        admin_text = NotionMessages.notion_admin_approval_request(
            username=callback.from_user.username,
            notion_user_name=selected_user["name"]
        )


# Шаг 4: Выбор статуса при создании задачи (кнопка)
@router.callback_query(NotionRegistrationStates.waiting_for_created_status, F.data.startswith("select_status:"))
async def process_created_status_callback(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    options = data.get("status_options", [])
    try:
        idx = int(callback.data.split(":")[1])
        status_name = options[idx]
    except (IndexError, ValueError):
        await callback.answer()
        return

    await state.update_data(notion_status_created=status_name)
    await state.set_state(NotionRegistrationStates.waiting_for_completed_status)
    await callback.answer()
    await callback.message.edit_text(
        text=NotionMessages.ask_completed_status(),
        reply_markup=get_status_selection_keyboard(options),
        parse_mode="HTML"
    )


# Шаг 4: Выбор статуса при создании задачи (вручную текстом)
@router.message(NotionRegistrationStates.waiting_for_created_status)
async def process_created_status_text(message: Message, state: FSMContext):
    text = message.text.strip() if message.text else ""
    data = await state.get_data()
    options = data.get("status_options", [])

    matched = next((opt for opt in options if opt.lower() == text.lower()), None)
    if matched:
        await state.update_data(notion_status_created=matched)
        await state.set_state(NotionRegistrationStates.waiting_for_completed_status)
        await message.answer(
            text=NotionMessages.ask_completed_status(),
            reply_markup=get_status_selection_keyboard(options),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            text=NotionMessages.invalid_status_selection(),
            reply_markup=get_status_selection_keyboard(options),
            parse_mode="HTML"
        )


# Шаг 5: Выбор статуса при выполнении задачи (кнопка)
@router.callback_query(NotionRegistrationStates.waiting_for_completed_status, F.data.startswith("select_status:"))
async def process_completed_status_callback(callback: CallbackQuery, state: FSMContext, db: Connection, bot: Bot):
    data = await state.get_data()
    options = data.get("status_options", [])
    try:
        idx = int(callback.data.split(":")[1])
        status_name = options[idx]
    except (IndexError, ValueError):
        await callback.answer()
        return

    token = data.get("token")
    db_id = data.get("db_id")
    created_status = data.get("notion_status_created")
    selected_user_id = data.get("selected_user_id")
    selected_user_name = data.get("selected_user_name")
    multi_select_options = data.get("multi_select_options", [])

    import json
    # Сохраняем все настройки Notion в БД
    await update_user_notion(
        db=db,
        tg_id=callback.from_user.id,
        notion_token=token,
        notion_db_id=db_id,
        notion_status_created=created_status,
        notion_status_completed=status_name,
        notion_statuses=json.dumps(options, ensure_ascii=False),
        notion_multi_selects=json.dumps(multi_select_options, ensure_ascii=False)
    )

    # Сохраняем выбранного пользователя как ожидающего одобрения
    await update_user_pending_notion(
        db=db,
        tg_id=callback.from_user.id,
        pending_id=selected_user_id,
        pending_name=selected_user_name
    )

    await state.clear()
    await callback.answer()
    
    await callback.message.edit_text(
        text=NotionMessages.notion_user_approval_pending(),
        parse_mode="HTML"
    )

    # Уведомляем администраторов
    admin_markup = get_admin_approval_keyboard(callback.from_user.id)
    admin_text = NotionMessages.notion_admin_approval_request(
        username=callback.from_user.username,
        notion_user_name=selected_user_name
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                reply_markup=admin_markup,
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Failed to notify admin {admin_id}: {e}")


# Шаг 5: Выбор статуса при выполнении задачи (вручную текстом)
@router.message(NotionRegistrationStates.waiting_for_completed_status)
async def process_completed_status_text(message: Message, state: FSMContext, db: Connection, bot: Bot):
    text = message.text.strip() if message.text else ""
    data = await state.get_data()
    options = data.get("status_options", [])

    matched = next((opt for opt in options if opt.lower() == text.lower()), None)
    if matched:
        token = data.get("token")
        db_id = data.get("db_id")
        created_status = data.get("notion_status_created")
        selected_user_id = data.get("selected_user_id")
        selected_user_name = data.get("selected_user_name")
        multi_select_options = data.get("multi_select_options", [])

        import json
        await update_user_notion(
            db=db,
            tg_id=message.from_user.id,
            notion_token=token,
            notion_db_id=db_id,
            notion_status_created=created_status,
            notion_status_completed=matched,
            notion_statuses=json.dumps(options, ensure_ascii=False),
            notion_multi_selects=json.dumps(multi_select_options, ensure_ascii=False)
        )

        await update_user_pending_notion(
            db=db,
            tg_id=message.from_user.id,
            pending_id=selected_user_id,
            pending_name=selected_user_name
        )

        await state.clear()
        await message.answer(
            text=NotionMessages.notion_user_approval_pending(),
            parse_mode="HTML",
            reply_markup=get_main_kb()
        )

        # Уведомляем администраторов
        admin_markup = get_admin_approval_keyboard(message.from_user.id)
        admin_text = NotionMessages.notion_admin_approval_request(
            username=message.from_user.username,
            notion_user_name=selected_user_name
        )
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=admin_text,
                    reply_markup=admin_markup,
                    parse_mode="HTML"
                )
            except Exception as e:
                logging.error(f"Failed to notify admin {admin_id}: {e}")
    else:
        await message.answer(
            text=NotionMessages.invalid_status_selection(),
            reply_markup=get_status_selection_keyboard(options),
            parse_mode="HTML"
        )


# Обработка текстового ввода для поиска участников по почте или имени (поддерживает частичное совпадение)
@router.message(NotionRegistrationStates.waiting_for_user_selection)
async def process_notion_user_text(message: Message, state: FSMContext, db: Connection):
    query = message.text.strip().lower() if message.text else ""
    tg_id = message.from_user.id

    if not query:
        await message.answer(
            text=NotionMessages.notion_users_loaded_search_prompt(),
            parse_mode="HTML"
        )
        return

    # Загружаем участников из базы данных
    cached_users = await get_cached_notion_users(db, tg_id)

    filtered_users = []
    for u in cached_users:
        name = (u.get("name") or "").lower()
        email = (u.get("email") or "").lower()
        # Поиск подстроки (частичное совпадение) в имени или почте
        if query in name or query in email:
            filtered_users.append(u)

    if filtered_users:
        # Сохраняем найденных пользователей в FSM state, чтобы callback_query мог их извлечь по индексу
        await state.update_data(notion_users=filtered_users)
        kb = get_notion_users_keyboard(filtered_users)
        await message.answer(
            text=NotionMessages.notion_users_found(),
            reply_markup=kb,
            parse_mode="HTML"
        )
    else:
        # Если совпадений нет, выводим сообщение об ошибке
        await message.answer(
            text=NotionMessages.notion_user_not_found_retry(),
            parse_mode="HTML"
        )
