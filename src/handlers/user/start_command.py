import html

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.filters import CommandStart, CommandObject

from src.database import channels
from src.keyboards.user import UserKeyboards
from src.messages.user import UserMessages
from src.database.users import create_user_if_not_exist


async def handle_start_command(message: Message, state: FSMContext):
    await state.clear()

    user = message.from_user
    create_user_if_not_exist(telegram_id=user.id, firstname=user.first_name, username=user.username)

    await message.answer_photo(
        photo=UserMessages.get_welcome_photo(),
        caption=UserMessages.get_welcome(user_name=user.first_name),
        reply_markup=UserKeyboards.get_main_menu()
    )


async def handle_share_channel_start_command(message: Message, command: CommandObject):
    user = message.from_user
    created_user = create_user_if_not_exist(telegram_id=user.id, firstname=user.first_name, username=user.username)

    secret_code = command.args.replace('share_', '')
    shared_channel = channels.get_channel_by_secret_code(code=secret_code)

    if not shared_channel:
        await message.answer(text='Ссылка устарела!')
        return

    channels.add_writer_to_channel(user=created_user, channel=shared_channel)
    channels.update_channel_secret_code(channel=shared_channel)
    await message.answer(
        text=f'Теперь вы можете редактировать канал {shared_channel}',
        reply_markup=UserKeyboards.get_main_menu()
    )

    await message.bot.send_message(
        chat_id=shared_channel.creator.telegram_id,
        text=f'Пользователь <b>{html.escape(user.full_name)}</b> стал редактором канала <b>{shared_channel}</b>.'
    )


def register_menu_handlers(router: Router):
    # При добавлении редактора
    router.message.register(
        handle_share_channel_start_command, CommandStart(deep_link=True, magic=F.args.startswith('share_'))
    )

    # Команда /start
    router.message.register(handle_start_command, CommandStart(deep_link=False))
