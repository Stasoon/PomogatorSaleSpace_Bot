from datetime import date
from typing import Optional

from aiogram.filters.callback_data import CallbackData


class ChannelCallback(CallbackData, prefix='channel'):
    channel_id: int
    action: str


class NavigationCallback(CallbackData, prefix='navigation'):
    branch: Optional[str] = None


class CalendarNavigationCallback(CallbackData, prefix='calendar_nav'):
    year: int
    month: int
    channel_id: Optional[int] = None


class DateCallback(CallbackData, prefix='date'):
    date: date
    action: Optional[str] = None
    channel_id: Optional[int] = None


class PublicationFormatCallback(CallbackData, prefix='publication_format'):
    publication_format: str


class SaleCallback(CallbackData, prefix='sale'):
    sale_id: int


class EditSaleCallback(CallbackData, prefix='edit_sale'):
    sale_id: int
    option: str
