from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from src.database import channels
from src.keyboards.user import UserKeyboards
from src.messages.user import UserMessages
from src.misc.callbacks_data import NavigationCallback, ChannelCallback


def __get_settings_message_data(user_id: int) -> dict:
    user_channels = channels.get_user_channels(user=user_id)
    markup = UserKeyboards.get_channels_for_settings(channels=user_channels)
    return {'text': '🔍 Выберите канал:', 'reply_markup': markup}


async def handle_settings_button_message(message: Message):
    if not channels.get_user_channels(user=message.from_user.id):
        await message.answer(UserMessages.get_add_channels_first())
        return

    await message.answer(**__get_settings_message_data(user_id=message.from_user.id))


async def handle_back_to_settings_callback(callback: CallbackQuery):
    await callback.message.edit_text(**__get_settings_message_data(user_id=callback.from_user.id))


async def handle_channel_to_settings_callback(callback: CallbackQuery, callback_data: ChannelCallback):
    channel = channels.get_channel_by_id(channel_id=callback_data.channel_id)
    bot_username = (await callback.bot.get_me()).username
    await callback.message.edit_text(
        text=f'⚙ Настройки канала {channel}',
        reply_markup=UserKeyboards.get_channel_settings(channel=channel, bot_username=bot_username)
    )


def register_channels_handlers(router: Router):
    router.message.register(handle_settings_button_message, F.text.lower().contains('каналы'))

    router.callback_query.register(
        handle_back_to_settings_callback, NavigationCallback.filter(F.branch == 'channels')
    )

    router.callback_query.register(handle_channel_to_settings_callback, ChannelCallback.filter(F.action == 'channels'))
