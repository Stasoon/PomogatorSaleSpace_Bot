import json
import datetime

from aiogram import Router, F, Bot
from aiogram.enums import ContentType
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from src.database.models import Sale, User, Channel
from src.database.sale_payments_remindres import create_sale_payment_reminder
from src.keyboards.user import UserKeyboards
from src.messages.user import UserMessages
from src.database.users import get_user_or_none
from src.database import channels, sales
from src.misc.callbacks_data import ChannelCallback, DateCallback, CalendarNavigationCallback
from src.misc.enums import SalePaymentStatusEnum
from src.misc.states.user import PurchaseAddingStates
from src.utils import GoogleSheetsAPI


# region Utils


def __get_table_name(channel_name: str) -> str:
    return f"Продажи {channel_name}"


def get_table_title() -> list[str]:
    return [
        "Дата", "Время", "Покупатель",
        "Стоимость", "Процент менеджеру",
        "Формат публикации", "Статус оплаты"
    ]

# endregion


async def handle_create_purchase_callback(message: Message, state: FSMContext):
    await message.answer(
        text=UserMessages.get_create_purchase(),
        reply_markup=UserKeyboards.get_cancel_reply()
    )

    user = get_user_or_none(telegram_id=message.from_user.id)
    user_channels = channels.get_user_channels(user=user)
    markup = UserKeyboards.get_channels_to_create_purchase(user_channels)

    if len(user_channels) == 0:
        text = "🪬Введите название канала:"
    else:
        text = "🪬Выберите канал из списка или напишите название для добавления нового канала:"

    await message.answer(text=text, reply_markup=markup)
    await state.set_state(PurchaseAddingStates.select_channel)


async def handle_cancel_creating_message(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(text="Создание продажи отменено", reply_markup=ReplyKeyboardRemove())
    await message.answer(text=UserMessages.get_main_menu(), reply_markup=UserKeyboards.get_main_menu())


async def handle_channel_callback(callback: CallbackQuery, callback_data: ChannelCallback, state: FSMContext):
    await state.update_data(channel_id=callback_data.channel_id)

    current_date = datetime.date.today()

    await callback.message.edit_text(
        text=UserMessages.ask_for_publication_date(),
        reply_markup=UserKeyboards.get_calendar(year=current_date.year, month_num=current_date.month)
    )
    await state.set_state(PurchaseAddingStates.select_date)


async def handle_new_channel_title_message(message: Message, state: FSMContext):
    user = get_user_or_none(telegram_id=message.from_user.id)
    channel = channels.create_channel(creator=user, channel_title=message.text)
    await state.update_data(channel_id=channel.id)

    current_date = datetime.date.today()

    await message.answer(
        text=UserMessages.ask_for_publication_date(),
        reply_markup=UserKeyboards.get_calendar(year=current_date.year, month_num=current_date.month)
    )
    await state.set_state(PurchaseAddingStates.select_date)


async def handle_calendar_navigation_callback(callback: CallbackQuery, callback_data: CalendarNavigationCallback):
    markup = UserKeyboards.get_calendar(year=callback_data.year, month_num=callback_data.month)
    await callback.message.edit_reply_markup(reply_markup=markup)


async def handle_date_callback(callback: CallbackQuery, callback_data: DateCallback, state: FSMContext):
    await state.update_data(date=callback_data.date)

    markup = UserKeyboards.get_select_time()
    publication_date = callback_data.date.strftime('%d.%m.%Y')

    await callback.message.edit_text(text=f"⏰ Дата публикации: {publication_date}")
    msg = await callback.message.answer(text="⌛ Время публикации:", reply_markup=markup)
    await state.update_data(previous_message_id=msg.message_id)
    await state.set_state(PurchaseAddingStates.select_time)


async def __process_time(user_id: int, bot: Bot, state: FSMContext, hour: int, minute: int):
    await bot.send_message(
        chat_id=user_id,
        text=f"⌛ Время публикации: {hour:02}:{minute:02}",
        reply_markup=UserKeyboards.get_cancel_reply()
    )
    previous_message_id = (await state.get_data()).get("previous_message_id")
    await bot.delete_message(chat_id=user_id, message_id=previous_message_id)

    await state.update_data(time=datetime.time(hour=hour, minute=minute))
    await state.set_state(PurchaseAddingStates.enter_buyer)
    await bot.send_message(chat_id=user_id, text="👤 Напишите @username или имя покупателя:")


async def handle_selected_time_web_app_data(message: Message, state: FSMContext):
    await message.delete()

    data = json.loads(message.web_app_data.data)
    hour, minute = data.get("hours"), data.get("minutes")

    await __process_time(user_id=message.from_user.id, bot=message.bot, state=state, hour=hour, minute=minute)


async def handle_time_message(message: Message, state: FSMContext):
    a = message.text.split(":")
    input_error_text = "Введите время в формате Часы:Минуты или воспользуйтесь клавиатурой!"
    if len(a) != 2:
        await message.answer(text=input_error_text)
        return

    hours_text, minutes_text = a

    is_correct = hours_text.isdigit() and 0 <= int(hours_text) <= 24 \
                 and minutes_text.isdigit() and 0 <= int(minutes_text) <= 59
    if not is_correct:
        await message.answer(input_error_text)
        return

    hour = int(hours_text)
    minute = int(minutes_text)
    await __process_time(user_id=message.from_user.id, bot=message.bot, state=state, hour=hour, minute=minute)


async def handle_buyer_title_message(message: Message, state: FSMContext):
    await state.update_data(buyer=message.text)

    await state.set_state(PurchaseAddingStates.enter_publication_format)
    await message.answer("🗑 Выберите формат публикации:", reply_markup=UserKeyboards.get_publication_formats())


async def handle_publication_format_message(message: Message, state: FSMContext):
    await state.update_data(publication_format=message.text)

    await state.set_state(PurchaseAddingStates.enter_publication_cost)
    await message.answer("💰Напишите цену рекламного места:", reply_markup=UserKeyboards.get_cancel_reply())


async def handle_publication_cost_message(message: Message, state: FSMContext):
    try:
        cost = round(float(message.text), 2)
    except ValueError:
        await message.answer("Это не число! Введите стоимость публикации:")
        return

    await state.update_data(publication_cost=cost)

    await message.answer(text=f"💰 Напишите <b>%</b> менеджеру:")
    await state.set_state(PurchaseAddingStates.enter_manager_percent)


async def handle_manager_percent_message(message: Message, state: FSMContext):
    text = message.text.replace("%", "")

    if text.isdigit():
        manager_percent = int(message.text)
    else:
        try:
            manager_percent = round(float(text), 2)
        except ValueError:
            manager_percent = None

    if manager_percent is None:
        await message.answer("Это не число! Введите процент менеджера:")
        return

    if manager_percent > 100:
        await message.answer("Процент не может быть больше 100. Попробуйте ещё раз:")
        return

    await state.update_data(manager_percent=manager_percent)
    await message.answer(text=f"💳 Выберите статус оплаты:", reply_markup=UserKeyboards.get_payment_statuses())
    await state.set_state(PurchaseAddingStates.enter_payment_status)


async def handle_payment_status(message: Message, state: FSMContext):
    if message.text not in tuple(SalePaymentStatusEnum):
        await message.answer(
            text=UserMessages.get_unknown_command(),
            reply_markup=UserKeyboards.get_payment_statuses()
        )
        return
    await state.update_data(payment_status=message.text)

    data = await state.get_data()
    await state.clear()

    # Saving to DB
    user = get_user_or_none(telegram_id=message.from_user.id)
    channel = channels.get_channel_by_id(channel_id=data.get("channel_id"))
    new_sale = __write_sale_to_db(user=user, channel=channel, state_data=data)

    # Finish sale creation
    await __finish_sale_creation(bot=message.bot, user_id=message.from_user.id, created_sale=new_sale)

    if user.telegram_id != channel.creator.telegram_id:
        await message.bot.send_message(
            chat_id=channel.creator.telegram_id,
            text=UserMessages.get_purchase_notification_for_owner(user, new_sale)
        )
    __setup_sale_payment_reminder(sale=new_sale)


def __write_sale_to_db(user: User, channel: Channel, state_data: dict):
    """ Saves created sale to the database """
    timestamp = datetime.datetime.combine(state_data.get("date"), state_data.get("time"))
    new_purchase = sales.create_sale(
        user=user,
        buyer=state_data.get("buyer"),
        channel=channel,
        timestamp=timestamp,
        publication_format=state_data.get("publication_format"),
        manager_percent=state_data.get("manager_percent"),
        payment_status=state_data.get("payment_status"),
        publication_cost=state_data.get("publication_cost")
    )
    return new_purchase


async def __finish_sale_creation(user_id: int, bot: Bot, created_sale: Sale):
    manager_profit = created_sale.publication_cost * (created_sale.manager_percent / 100)

    await bot.send_message(
        chat_id=user_id,
        text=f"<b>📄 Отчет TeleУчетка</b> \n\n"
        f"Запланировано рекламное место на {created_sale.get_date_str()} {created_sale.get_time_str()} \n"
        f"Стоимость рекламного места: {created_sale.publication_cost}₽ \n\n"
        f"<tg-spoiler>Процент менеджеру: {created_sale.manager_percent}% <b>({manager_profit:.2f}₽)</b></tg-spoiler>",
        reply_markup=ReplyKeyboardRemove()
    )
    msg = await bot.send_animation(
        chat_id=user_id,
        animation=UserMessages.get_loading_animation(), caption='Загрузка таблицы...'
    )

    table_url = await __write_sale_to_google_table(sale=created_sale)

    month_profit = sales.get_purchases_sum_for_month(
        year=created_sale.timestamp.year, month=created_sale.timestamp.month, channel=created_sale.channel
    )
    manager_month_profit = sales.get_manager_sum_for_month(
        year=created_sale.timestamp.year, month=created_sale.timestamp.month, channel=created_sale.channel
    )
    text = (
        f'<b>Общий итог продаж за {UserMessages.get_month_name(month_num=created_sale.timestamp.month)}</b> \n\n'
        f'Доход: {month_profit:.2f} ₽ \n'
        f'Доход менеджера за месяц: {manager_month_profit:.2f} ₽'
    )
    await msg.delete()
    await bot.send_message(chat_id=user_id, text=text, reply_markup=UserKeyboards.get_table(table_url=table_url))
    await bot.send_message(chat_id=user_id, text=UserMessages.get_main_menu(), reply_markup=UserKeyboards.get_main_menu())


def __setup_sale_payment_reminder(sale: Sale):
    if sale.payment_status in (SalePaymentStatusEnum.BY_SPM.value, SalePaymentStatusEnum.BOOKED.value):
        if sale.payment_status == SalePaymentStatusEnum.BY_SPM.value:
            reminder_time = sale.timestamp + datetime.timedelta(hours=23, minutes=58)
        else:
            reminder_time = sale.timestamp - datetime.timedelta(hours=24)

        # Skip if reminder outdated
        if datetime.datetime.now() > reminder_time:
            return
        else:
            create_sale_payment_reminder(sale_id=sale.id, reminder_time=reminder_time)


async def __write_sale_to_google_table(sale: Sale) -> str:
    # Занесение данных в таблицу
    table_name = __get_table_name(channel_name=sale.channel.title)

    if not sale.channel.table_id:
        table_id = await GoogleSheetsAPI.create_table(table_name=table_name, title_data=get_table_title())
        sale.channel.table_id = table_id
        sale.channel.save()

    data = [
        sale.get_date_str(), sale.get_time_str(),
        sale.buyer, sale.publication_cost,
        sale.manager_percent, sale.publication_format,
        sale.payment_status
    ]
    record_number = sales.get_sales_count_in_channel(channel=sale.channel)
    table_url = await GoogleSheetsAPI.insert_row_data(
        table_id=sale.channel.table_id, data=data, position=record_number
    )

    return table_url


def register_purchases_handlers(router: Router):
    # Создать продажу
    router.message.register(
        handle_create_purchase_callback, F.text.lower().contains('создать продажу')
    )

    # Отмена
    router.message.register(
        handle_cancel_creating_message,
        F.text.lower().contains('отменить'),
        StateFilter(PurchaseAddingStates)
    )

    # Выбор канала
    router.callback_query.register(
        handle_channel_callback,
        ChannelCallback.filter(F.action == 'create_purchase'),
        PurchaseAddingStates.select_channel
    )

    router.message.register(handle_new_channel_title_message, PurchaseAddingStates.select_channel)

    # Выбор даты в календаре
    router.callback_query.register(
        handle_date_callback,
        DateCallback.filter(F.action == 'select'),
        PurchaseAddingStates.select_date
    )
    # Навигация по календарю
    router.callback_query.register(
        handle_calendar_navigation_callback,
        CalendarNavigationCallback.filter(),
        PurchaseAddingStates.select_date
    )

    # Ввод времени из WebApp
    router.message.register(
        handle_selected_time_web_app_data, F.content_type == ContentType.WEB_APP_DATA, PurchaseAddingStates.select_time
    )
    router.message.register(handle_time_message, PurchaseAddingStates.select_time, PurchaseAddingStates.select_time)

    # Название покупателя
    router.message.register(handle_buyer_title_message, PurchaseAddingStates.enter_buyer)

    # Формат публикации
    router.message.register(
        handle_publication_format_message,
        PurchaseAddingStates.enter_publication_format
    )

    # Стоимость публикации
    router.message.register(handle_publication_cost_message, PurchaseAddingStates.enter_publication_cost)

    # Процент менеджеру
    router.message.register(handle_manager_percent_message, PurchaseAddingStates.enter_manager_percent)

    # Статус оплаты
    router.message.register(handle_payment_status, PurchaseAddingStates.enter_payment_status)
