from aiogram.fsm.state import State, StatesGroup


class TaskStates(StatesGroup):
    waiting_for_task = State()