from aiogram.fsm.state import StatesGroup, State


class PurchaseAddingStates(StatesGroup):
    select_channel = State()
    select_date = State()
    select_time = State()
    enter_buyer = State()
    enter_publication_format = State()
    enter_publication_cost = State()
    enter_manager_percent = State()
    enter_payment_status = State()