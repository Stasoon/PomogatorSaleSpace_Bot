import calendar
from datetime import date

from aiogram.types import KeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardBuilder

from src.database.models import Channel, Sale
from src.misc.callbacks_data import ChannelCallback, NavigationCallback, CalendarNavigationCallback, DateCallback, \
    SaleCallback, EditSaleCallback
from src.misc.enums import SalePaymentStatusEnum
from src.utils import GoogleSheetsAPI


def convert_number_to_dots(n: int):
    return f"{':' * (n//2)}{'.' * (n%2)}"


months_words = (
    '', 'Январь', 'Февраль', 'Март', 'Апрель',
    'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь',
    'Октябрь', 'Ноябрь', 'Декабрь'
)

days_short_names = (
    'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Cб', 'Вс'
)

weekdays = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]


class UserKeyboards:

    @staticmethod
    def get_cancel_reply() -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='❌ Отменить')]], resize_keyboard=True)

    @staticmethod
    def get_main_menu() -> ReplyKeyboardMarkup:
        builder = ReplyKeyboardBuilder()

        builder.button(text='Создать продажу')
        builder.button(text='Календарь продаж')
        builder.button(text='Общий доход')
        builder.button(text='Каналы')

        builder.adjust(1)
        return builder.as_markup(resize_keyboard=True, is_presistance=True)

    @staticmethod
    def get_channels(channels: list[Channel]) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        for channel in channels:
            callback_data = ChannelCallback(channel_id=channel.id, action='show')
            builder.button(text=str(channel), callback_data=callback_data)

        # builder.button(text='➕ Добавить', callback_data=NavigationCallback(branch='add_channel'))
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def get_channel_settings(channel: Channel, bot_username: str) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        channel_share_url = f'tg://msg_url?url=https://t.me/{bot_username}?start=share_{channel.secret_code}'
        builder.button(text='Добавить редактора', url=channel_share_url)

        if channel.table_id:
            channel_table_url = GoogleSheetsAPI.get_table_url(table_id=channel.table_id)
            builder.button(text='Таблица продаж', url=channel_table_url)

        builder.button(text='🔙 Назад', callback_data=NavigationCallback(branch='channels'))

        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def __get_channels_list(channels: list[Channel], action: str) -> InlineKeyboardBuilder:
        builder = InlineKeyboardBuilder()

        for channel in channels:
            callback_data = ChannelCallback(channel_id=channel.id, action=action)
            builder.button(text=str(channel), callback_data=callback_data)
        return builder

    @classmethod
    def get_channels_to_create_purchase(cls, channels: list[Channel]) -> InlineKeyboardMarkup:
        builder = cls.__get_channels_list(channels=channels, action='create_purchase')
        builder.adjust(1)
        return builder.as_markup()

    @classmethod
    def get_channels_to_show_calendar(cls, channels: list[Channel]) -> InlineKeyboardMarkup:
        builder = cls.__get_channels_list(channels=channels, action='calendar')
        builder.adjust(1)
        return builder.as_markup()

    @classmethod
    def get_channels_for_settings(cls, channels: list[Channel]) -> InlineKeyboardMarkup:
        builder = cls.__get_channels_list(channels=channels, action='channels')
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def __get_calendar_navigation_builder(year: int, month: int, channel_id: int = None) -> InlineKeyboardBuilder:
        nav_builder = InlineKeyboardBuilder()
        nav_builder.button(
            text='◀', callback_data=CalendarNavigationCallback(
                year=year if month > 1 else year - 1,
                month=month - 1 if month > 1 else 12,
                channel_id=channel_id
            )
        )
        nav_builder.button(
            text='▶', callback_data=CalendarNavigationCallback(
                year=year if month < 12 else year + 1,
                month=month + 1 if month < 12 else 1,
                channel_id=channel_id
            )
        )
        nav_builder.adjust(2)
        return nav_builder

    @classmethod
    def get_calendar(cls, year: int, month_num: int) -> InlineKeyboardMarkup:
        days_builder = InlineKeyboardBuilder()
        days_builder.button(text=f'{months_words[month_num]} {year}', callback_data='*')
        [days_builder.button(text=days_short_names[day_num], callback_data='*') for day_num in range(7)]

        cal = calendar.Calendar()
        for week in cal.monthdayscalendar(year=year, month=month_num):
            for day in week:
                day_text = str(day) if day else ' '
                callback_data = DateCallback(
                    date=date(year=year, month=month_num, day=day), action='select'
                ) if day else '*'
                days_builder.button(text=day_text, callback_data=callback_data)

        days_builder.adjust(1, 7)
        nav_builder = cls.__get_calendar_navigation_builder(year=year, month=month_num)
        return days_builder.attach(nav_builder).as_markup()

    @staticmethod
    def get_select_time() -> ReplyKeyboardMarkup:
        builder = ReplyKeyboardBuilder()

        builder.button(text='✍ Ввести', web_app=WebAppInfo(url='https://stasoon.github.io/enter_time_web_app.html'))
        builder.button(text='❌ Отменить')

        builder.adjust(1)
        return builder.as_markup(resize_keyboard=True)

    @staticmethod
    def get_table(table_url: str) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(text='# Таблица', url=table_url)
        return builder.as_markup()

    @classmethod
    def get_channel_purchases_calendar(
            cls, channel_id: int, days_purchases_count: dict[int, int], year: int, month_num: int
    ) -> InlineKeyboardMarkup:
        days_builder = InlineKeyboardBuilder()
        days_builder.button(text=f'{months_words[month_num]} {year}', callback_data='*')
        [days_builder.button(text=days_short_names[day_num], callback_data='*') for day_num in range(7)]

        cal = calendar.Calendar()

        for week in cal.monthdayscalendar(year=year, month=month_num):
            for day in week:
                events_count = days_purchases_count.get(day)
                count_text = f"|{convert_number_to_dots(events_count)}" if events_count else ''
                day_text = f"{day}{count_text}" if day else ' '
                callback_data = DateCallback(
                 date=date(year=year, month=month_num, day=day), action='show_events', channel_id=channel_id
                ) if day else '*'
                days_builder.button(text=day_text, callback_data=callback_data)

        days_builder.adjust(1, 7)

        nav_builder = cls.__get_calendar_navigation_builder(year=year, month=month_num, channel_id=channel_id)
        nav_builder.button(text='🔙 Назад', callback_data=NavigationCallback(branch='sales_calendar'))
        nav_builder.adjust(2, 1, 1)
        return days_builder.attach(nav_builder).as_markup()

    @staticmethod
    def get_channels_for_total_profit(channels: list[Channel]) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for channel in channels:
            builder.button(
                text=f"{channel.title}",
                callback_data=ChannelCallback(channel_id=channel.id, action='show_total_profit')
            )

        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def get_publication_formats() -> ReplyKeyboardMarkup:
        builder = ReplyKeyboardBuilder()

        builder.button(text='1/1')
        builder.button(text='1/24')

        builder.button(text='1/48')
        builder.button(text='1/72')

        builder.button(text='Без удаления')
        builder.button(text='❌ Отменить')

        builder.adjust(2, 2, 1, 1)
        return builder.as_markup(input_field_placeholder='Выберите или введите формат')

    @staticmethod
    def get_payment_statuses() -> ReplyKeyboardMarkup:
        cancel_builder = ReplyKeyboardBuilder()
        cancel_builder.button(text='❌ Отменить')

        builder = ReplyKeyboardBuilder()
        for status in SalePaymentStatusEnum:
            builder.button(text=status.value)

        builder.adjust(2).attach(cancel_builder)
        return builder.as_markup(input_field_placeholder='Выберите статус оплаты:', resize_keyboard=True)

    @staticmethod
    def get_open_sale(sale: Sale) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        month_str = f"{months_words[sale.timestamp.month].lower()[:3]}."
        time_str = sale.get_time_str()
        weekday_str = weekdays[sale.timestamp.weekday()]

        text = f'{weekday_str} {sale.timestamp.day} {month_str} {time_str} → {sale.buyer}'
        builder.button(text=text, callback_data=SaleCallback(sale_id=sale.id))
        return builder.as_markup()

    @staticmethod
    def get_day_sales(sales: list[Sale]) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        for sale in sales:
            month_str = f"{months_words[sale.timestamp.month].lower()[:3]}."
            time_str = sale.get_time_str()
            weekday_str = weekdays[sale.timestamp.weekday()]

            text = f'{weekday_str} {sale.timestamp.day} {month_str} {time_str} → {sale.buyer}'
            builder.button(text=text, callback_data=SaleCallback(sale_id=sale.id))

        sale = sales[0]
        builder.button(
            text='🔙 Назад', callback_data=CalendarNavigationCallback(
                year=sale.timestamp.year, month=sale.timestamp.month, channel_id=sale.channel.id
            )
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def get_sale_editing(sale: Sale, has_rights_on_delete: bool = False) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(text='Изменить % менеджеру', callback_data=EditSaleCallback(sale_id=sale.id, option='manager_percent'))
        builder.button(text='Изменить цену места', callback_data=EditSaleCallback(sale_id=sale.id, option='cost'))
        builder.button(text='Изменить формат', callback_data=EditSaleCallback(sale_id=sale.id, option='format'))
        builder.button(text='Изменить статус', callback_data=EditSaleCallback(sale_id=sale.id, option='payment_status'))
        builder.button(text='Изменить покупателя', callback_data=EditSaleCallback(sale_id=sale.id, option='buyer'))
        if has_rights_on_delete:
            builder.button(text='❌ Удалить', callback_data=EditSaleCallback(sale_id=sale.id, option='delete'))
        builder.button(text='🔙 Назад', callback_data=DateCallback(date=sale.timestamp.date(), channel_id=sale.channel.id))

        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def get_back_to_total_profits() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(text='🔙 Назад', callback_data=NavigationCallback(branch='total_profit'))
        return builder.as_markup()
