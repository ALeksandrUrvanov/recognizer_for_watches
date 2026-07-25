from aiogram.fsm.state import State, StatesGroup


class RecognitionStates(StatesGroup):
    """Состояния FSM для процесса распознавания часов"""
    
    waiting_photo = State()
    waiting_selection = State()

