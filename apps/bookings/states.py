from aiogram.fsm.state import State, StatesGroup


class BookingForm(StatesGroup):
    service = State()
    specialist = State()
    day = State()
    time = State()
    phone = State()
    confirm = State()
