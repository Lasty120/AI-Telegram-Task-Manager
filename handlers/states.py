from aiogram.fsm.state import StatesGroup, State

class NotionRegistrationStates(StatesGroup):
    waiting_for_token = State()
    waiting_for_db_id = State()
    waiting_for_data_source = State()
    waiting_for_created_status = State()
    waiting_for_completed_status = State()
    waiting_for_user_selection = State()