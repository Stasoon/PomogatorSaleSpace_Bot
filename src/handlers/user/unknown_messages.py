from aiogram import Router
from aiogram.types import Message

from src.keyboards.user import UserKeyboards
from src.messages.user import UserMessages


async def handle_unknown_messages(message: Message):
    await message.answer(text=UserMessages.get_unknown_command(), reply_markup=UserKeyboards.get_main_menu())


def register_unknown_messages_handler(router: Router):
    router.message.register(handle_unknown_messages)
