from aiogram import Router, F
from aiogram.types import CallbackQuery, Message

from src.database import channels, sales
from src.database.users import get_user_or_none
from src.keyboards.user import UserKeyboards
from src.misc.callbacks_data import NavigationCallback, ChannelCallback


async def handle_total_profit_button_message(message: Message):
    user = get_user_or_none(telegram_id=message.from_user.id)
    user_channels = channels.get_user_channels(user=user)

    await message.answer(
        text='Выберите канал для показа общего дохода:',
        reply_markup=UserKeyboards.get_channels_for_total_profit(channels=user_channels)
    )


async def handle_back_to_total_profit_callback(callback: CallbackQuery):
    user = get_user_or_none(telegram_id=callback.from_user.id)
    user_channels = channels.get_user_channels(user=user)

    await callback.message.edit_text(
        text='Выберите канал для показа общего дохода:',
        reply_markup=UserKeyboards.get_channels_for_total_profit(channels=user_channels)
    )


async def handle_show_channel_total_profit(callback: CallbackQuery, callback_data: ChannelCallback):
    await callback.answer()
    channel = channels.get_channel_by_id(channel_id=callback_data.channel_id)

    total_profit = sales.get_total_sales_sum(channel=channel)
    total_manager_profit = sales.get_total_manager_sum(channel=channel)
    await callback.message.edit_text(
        f'<b>{channel.title}</b> \n\n'
        f'Общий доход с канала: {total_profit:.2f} ₽ \n'
        f'Общий доход менеджера с канала: {total_manager_profit:.2f} ₽',
        reply_markup=UserKeyboards.get_back_to_total_profits()
    )


def register_total_profit_handlers(router: Router):
    router.message.register(
        handle_total_profit_button_message, F.text.lower().contains('общий доход')
    )

    router.callback_query.register(
        handle_back_to_total_profit_callback, NavigationCallback.filter(F.branch == 'total_profit')
    )

    router.callback_query.register(
        handle_show_channel_total_profit,
        ChannelCallback.filter(F.action == 'show_total_profit')
    )
