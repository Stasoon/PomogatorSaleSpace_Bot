import asyncio
import datetime

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.state import StatesGroup, State, default_state
from aiogram.types import Message, CallbackQuery

from src.keyboards.user import UserKeyboards
from src.messages.user import UserMessages
from src.database.users import get_user_or_none
from src.database import channels, sales
from src.misc.callbacks_data import NavigationCallback, ChannelCallback, CalendarNavigationCallback, DateCallback


class ChannelAddingStates(StatesGroup):
    wait_for_post = State()


def __get_user_channels_message_data(user_id: int):
    user = get_user_or_none(telegram_id=user_id)
    user_channels = channels.get_user_channels(user=user)

    text = UserMessages.get_my_channels()
    markup = UserKeyboards.get_channels(channels=user_channels)
    return {'text': text, 'reply_markup': markup}


async def handle_my_channels_message(message: Message):
    message_data = __get_user_channels_message_data(user_id=message.from_user.id)
    await message.answer(**message_data)


async def handle_back_to_my_channels_callback(callback: CallbackQuery):
    message_data = __get_user_channels_message_data(user_id=callback.from_user.id)
    await callback.message.edit_text(**message_data)


async def handle_channel_callback(callback: CallbackQuery, callback_data: ChannelCallback):
    channel = channels.get_channel_by_id(channel_id=callback_data.channel_id)
    bot_username = (await callback.bot.get_me()).username

    if not channels.is_user_channel_writer(channel=channel, user=callback.from_user.id):
        await handle_back_to_my_channels_callback(callback=callback)
        return

    is_channel_creator = (callback.from_user.id == channel.creator.telegram_id)
    markup = UserKeyboards.get_actions_with_channel(
        bot_username=bot_username, channel=channel, is_channel_creator=is_channel_creator
    )

    await callback.message.edit_text(text=f'📢 <b>{channel}</b>', reply_markup=markup)


async def handle_show_channel_calendar_callback(
        callback: CallbackQuery, callback_data: ChannelCallback | CalendarNavigationCallback
):

    if isinstance(callback_data, ChannelCallback):
        current_date = datetime.date.today()
        year, month = current_date.year, current_date.month
    else:
        year, month = callback_data.year, callback_data.month

    if not 2015 < year < 2100:
        return

    channel = channels.get_channel_by_id(callback_data.channel_id)

    if not channel:
        return

    month_profit = sales.get_purchases_sum_for_month(channel=channel, year=year, month=month)
    manager_profit = sales.get_manager_sum_for_month(channel=channel, year=year, month=month)

    text = UserMessages.get_channel_profit(
        manager_profit=manager_profit, month_profit=month_profit, channel_title=channel.title,
        month_num=month
    )

    days_purchases_count = sales.get_sales_counts_by_days(channel=channel, year=year, month=month)
    markup = UserKeyboards.get_channel_purchases_calendar(
        days_purchases_count=days_purchases_count,
        year=year, month_num=month, channel_id=channel.id
    )
    await callback.message.edit_text(text=text, reply_markup=markup)


async def handle_show_day_purchases_callback(callback: CallbackQuery, callback_data: DateCallback):
    await callback.answer()
    channel = channels.get_channel_by_id(callback_data.channel_id)

    purchases_in_day = sales.get_sales_by_day(channel_id=channel, purchase_date=callback_data.date)
    profit_in_day, manager_profit_in_day = 0, 0

    for purchase in purchases_in_day:
        date = purchase.timestamp.strftime('%d.%m.%Y')
        time = purchase.timestamp.strftime('%H:%M')

        manager_profit = purchase.manager_percent * purchase.publication_cost / 100
        manager_profit_in_day += manager_profit
        profit_in_day += purchase.publication_cost

        await callback.message.answer(
            f'Продажа на {date} {time} \n\n'
            f'Стоимость рекламного места: {purchase.publication_cost:.2f} ₽ \n'
            f'Процент менеджеру: {purchase.manager_percent:.2f}% <b>({manager_profit:.2f} ₽)</b> \n',
            disable_notification=True
        )
        await asyncio.sleep(0.05)

    markup = UserKeyboards.get_create_purchase_button(channel_id=channel.id, calendar_date=callback_data.date)
    if len(purchases_in_day) == 0:
        await callback.message.answer(
            text=f"Хотите создать продажу на {callback_data.date.strftime('%d.%m.%Y')} в канал {channel.title}?",
            reply_markup=markup
        )
    else:
        await callback.message.answer(
            text=f"Доход за день: {profit_in_day:.2f} ₽ \nДоход менеджера за день: {manager_profit_in_day:.2f} ₽",
            reply_markup=markup
        )


def register_channels_handlers(router: Router):
    # Мои каналы
    router.message.register(handle_my_channels_message, F.text.lower().contains('каналы'))

    # Возврат к списку каналов
    router.callback_query.register(
        handle_back_to_my_channels_callback, NavigationCallback.filter(F.branch == 'my_channels')
    )

    # Нажатие на канал
    router.callback_query.register(handle_channel_callback, ChannelCallback.filter(F.action == 'show'))

    # Нажатие на календарь продаж в канале
    router.callback_query.register(
        handle_show_channel_calendar_callback, ChannelCallback.filter(F.action == 'calendar')
    )

    # Навигация по календарю
    router.callback_query.register(
        handle_show_channel_calendar_callback,
        CalendarNavigationCallback.filter(F.channel_id),
        StateFilter(default_state)
    )

    # Нажатие на день с закупами
    router.callback_query.register(
        handle_show_day_purchases_callback,
        DateCallback.filter(F.channel_id),
        StateFilter(default_state)
    )
