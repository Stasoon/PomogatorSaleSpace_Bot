import datetime
from typing import Literal

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, StatesGroup, State
from aiogram.types import CallbackQuery, Message

from src.database import sales
from src.database import channels
from src.database.models import Sale
from src.messages.user import UserMessages
from src.keyboards.user import UserKeyboards
from src.misc.callbacks_data import NavigationCallback, DateCallback, ChannelCallback, CalendarNavigationCallback, \
    SaleCallback, EditSaleCallback
from src.utils import GoogleSheetsAPI


class SaleEditingStates(StatesGroup):
    enter_new_cost = State()
    enter_new_manager_percent = State()
    enter_new_format = State()
    enter_new_buyer = State()

    @classmethod
    def get_state(cls, option: Literal['cost', 'buyer', 'manager_percent', 'format']):
        match option:
            case 'cost': return cls.enter_new_cost
            case 'manager_percent': return cls.enter_new_manager_percent
            case 'buyer': return cls.enter_new_buyer
            case 'format': return cls.enter_new_format


def __get_message_data(user_id: int) -> dict:
    user_channels = channels.get_user_channels(user=user_id)
    markup = UserKeyboards.get_channels_to_show_calendar(channels=user_channels)
    return {'text': 'Выберите канал:', 'reply_markup': markup}


async def handle_sales_calendar_button_message(message: Message):
    await message.answer(**__get_message_data(user_id=message.from_user.id))


async def handle_back_from_calendar_callback(callback: CallbackQuery):
    await callback.message.edit_text(**__get_message_data(user_id=callback.from_user.id))


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
    sales_in_day = sales.get_sales_by_day(channel_id=channel, purchase_date=callback_data.date)

    if not sales_in_day:
        try:
            await handle_show_channel_calendar_callback(callback, ChannelCallback(channel_id=channel.id, action='calendar'))
        except TelegramBadRequest:
            pass
        return

    markup = UserKeyboards.get_day_sales(sales=sales_in_day)
    text = f"<b>🗓 {channel}</b> \n\nПродано мест:"
    await callback.message.edit_text(text=text, reply_markup=markup)


async def handle_show_sale_callback(callback: CallbackQuery, callback_data: SaleCallback):
    sale = sales.get_sale_by_id(sale_id=callback_data.sale_id)
    if not sale:
        return
    await __show_sale(callback.bot, callback.from_user.id, sale, callback.message.message_id)


async def __show_sale(bot: Bot, user_id: int, sale: Sale, edit_msg_id: int = None):
    text = (
        f'Менеджер: {sale.writer} \n'
        f'Процент менеджеру: {sale.manager_percent}% \n'
        f'Цена рекламного места: {sale.publication_cost:.2f} ₽ \n'
        f'Формат: {sale.publication_format} \n'
        f'Покупатель: {sale.buyer}'
    )
    has_rights_on_delete = sale.channel.creator.telegram_id == user_id or sale.writer.telegram_id == user_id
    markup = UserKeyboards.get_sale_editing(sale=sale, has_rights_on_delete=has_rights_on_delete)

    if edit_msg_id:
        await bot.edit_message_text(chat_id=user_id, text=text, reply_markup=markup, message_id=edit_msg_id)
    else:
        await bot.send_message(text=text, reply_markup=markup, chat_id=user_id)


async def handle_delete_sale_callback(callback: CallbackQuery, callback_data: EditSaleCallback):
    sale = sales.get_sale_by_id(sale_id=callback_data.sale_id)
    if not sale:
        return

    if sale.channel.creator.telegram_id != callback.from_user.id and sale.writer.telegram_id != callback.from_user.id:
        await callback.answer(UserMessages.get_not_enough_rights())
        return

    sale_number = sales.get_record_number_in_channel(sale=sale)
    print(sale_number)
    sales.delete_sale(sale_id=callback_data.sale_id)
    callback_data = DateCallback(date=sale.timestamp.date(), channel_id=sale.channel.id)
    await handle_show_day_purchases_callback(callback, callback_data)

    await GoogleSheetsAPI.delete_row(table_id=sale.channel.table_id, number=sale_number)


async def handle_edit_sale_callback(callback: CallbackQuery, callback_data: EditSaleCallback, state: FSMContext):
    await state.update_data(sale_id=callback_data.sale_id, option=callback_data.option)
    await state.set_state(SaleEditingStates.get_state(callback_data.option))
    await callback.message.edit_reply_markup(reply_markup=None)

    text, markup, col_number = None, None, None
    match callback_data.option:
        case 'cost':
            text = 'Введите новую цену:'
            col_number = 4
            markup = UserKeyboards.get_cancel_reply()
        case 'buyer':
            text = 'Введите нового продавца:'
            col_number = 3
            markup = UserKeyboards.get_cancel_reply()
        case 'manager_percent':
            text = 'Введите новый процент менеджеру:'
            col_number = 5
            markup = UserKeyboards.get_cancel_reply()
        case 'format':
            text = 'Выберите новый формат:'
            markup = UserKeyboards.get_publication_formats()
            col_number = 6

    await state.update_data(col_number=col_number)
    await callback.message.answer(text=text, reply_markup=markup)


async def handle_new_sale_data_message(message: Message, state: FSMContext):
    data = await state.get_data()
    sale = sales.get_sale_by_id(sale_id=data.get('sale_id'))

    if data.get('option') in ['cost', 'manager_percent']:
        try: float(message.text)
        except ValueError:
            await message.answer(text='Введите число:')
            return

    await state.clear()

    match data.get('option'):
        case 'cost': sale.publication_cost = float(message.text)
        case 'buyer': sale.buyer = message.text
        case 'format': sale.publication_format = message.text
        case 'manager_percent': sale.manager_percent = float(message.text)
    sale.save()

    await message.answer('✅ Изменения сохранены', reply_markup=UserKeyboards.get_main_menu())
    await __show_sale(bot=message.bot, user_id=message.from_user.id, sale=sale)
    await GoogleSheetsAPI.edit_cell(
        table_id=sale.channel.table_id, data=message.text, xy=(sale.id+1, data.get('col_number'))
    )


async def handle_cancel_editing(message: Message, state: FSMContext):
    await message.answer(text='Изменение отменено', reply_markup=UserKeyboards.get_main_menu())
    data = await state.get_data()
    sale = sales.get_sale_by_id(sale_id=data.get('sale_id'))
    await __show_sale(bot=message.bot, user_id=message.from_user.id, sale=sale)
    await state.clear()


def register_sales_calendar_handlers(router: Router):
    # Мои каналы
    router.message.register(handle_sales_calendar_button_message, F.text.lower().contains('календарь'))

    # Назад из календаря
    router.callback_query.register(
        handle_back_from_calendar_callback,
        NavigationCallback.filter(F.branch == 'sales_calendar')
    )

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

    # Нажатие на день с продажами
    router.callback_query.register(
        handle_show_day_purchases_callback,
        DateCallback.filter(F.channel_id),
        StateFilter(default_state)
    )

    # Нажатие на продажу
    router.callback_query.register(
        handle_show_sale_callback, SaleCallback.filter(), StateFilter(default_state)
    )

    # Изменение
    router.callback_query.register(handle_delete_sale_callback, EditSaleCallback.filter(F.option == 'delete'))
    router.callback_query.register(handle_edit_sale_callback, EditSaleCallback.filter())

    router.message.register(handle_cancel_editing, StateFilter(SaleEditingStates), F.text.lower().contains('отмен'))
    router.message.register(handle_new_sale_data_message, StateFilter(SaleEditingStates))
