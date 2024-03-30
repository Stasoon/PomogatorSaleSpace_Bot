import calendar
from datetime import datetime, date

from peewee import fn

from src.database.models import Sale, Channel, User


def create_sale(
        user: User, channel: Channel, buyer: str, timestamp: datetime,
        publication_cost: float, manager_percent: float,
        publication_format: str, row_in_table: int = None
) -> Sale:
    purchase = Sale.create(
        writer=user, channel=channel, timestamp=timestamp, buyer=buyer,
        publication_cost=publication_cost, manager_percent=manager_percent,
        publication_format=publication_format, row_in_table=row_in_table
    )
    return purchase


def get_sale_by_id(sale_id: int) -> Sale | None:
    return Sale.get_or_none(Sale.id == sale_id)


def get_sales_by_day(channel_id: int, purchase_date: date) -> list[Sale]:
    return (
        Sale
        .select()
        .where(
            (Sale.timestamp.day == purchase_date.day) &
            (Sale.timestamp.month == purchase_date.month) &
            (Sale.timestamp.year == purchase_date.year) &
            (Sale.channel == channel_id)
        )
        .order_by(Sale.timestamp)
    )


def get_sales_counts_by_days(channel: Channel, year: int, month: int) -> dict[int, int]:
    """ Возвращает словарь формата {день месяца: количество закупок} """
    last_day = calendar.monthrange(year, month)[1]
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)

    events_count_by_date = (
        Sale
        .select(fn.DATE(Sale.timestamp).alias('date'), fn.Count(Sale.id).alias('event_count'))
        .where(
            (fn.DATE(Sale.timestamp) >= start_date) &
            (fn.DATE(Sale.timestamp) <= end_date) &
            (Sale.channel == channel)
        )
        .group_by(fn.DATE(Sale.timestamp))
        .dicts()
    )

    result_dict = {event['date'].day: event['event_count'] for event in events_count_by_date}
    return result_dict


def get_total_sales_sum(channel: Channel) -> float:
    result = (
        Sale
        .select(fn.SUM(Sale.publication_cost))
        .where(Sale.channel == channel)
    )
    total = result.scalar() or 0.0
    return total


def get_purchases_sum_for_month(channel: Channel, year: int, month: int) -> float:
    first_date = date(year=year, month=month, day=1)
    end_date = date(year=year, month=month, day=calendar.monthrange(year=year, month=month)[1])

    result = (
        Sale
        .select(fn.SUM(Sale.publication_cost))
        .where(
            (Sale.channel == channel)
            & (Sale.timestamp >= first_date)
            & (Sale.timestamp <= end_date)
        )
    )

    total = result.scalar() or 0.0
    return total


def get_total_manager_sum(channel: Channel) -> float:
    result = (
        Sale
        .select(fn.SUM(Sale.publication_cost * Sale.manager_percent / 100))
        .where(Sale.channel == channel)
    )
    total = result.scalar() or 0.0
    return total


def get_manager_sum_for_month(channel: Channel, year: int, month: int) -> float:
    first_date = date(year=year, month=month, day=1)
    end_date = date(year=year, month=month, day=calendar.monthrange(year=year, month=month)[1])

    result = (
        Sale
        .select(fn.SUM(Sale.publication_cost * Sale.manager_percent / 100))
        .where(
            (Sale.channel == channel)
            & (Sale.timestamp >= first_date)
            & (Sale.timestamp <= end_date)
        )
    )
    total = result.scalar() or 0.0
    return total


def get_sales_count_in_channel(channel: Channel) -> int:
    return Sale.select().where(Sale.channel == channel).count()


def get_sales_in_channel(channel: Channel):
    return Sale.select().where(Sale.channel == channel)


def get_record_number_in_channel(sale):
    query = Sale.select(Sale.id).where(Sale.channel == sale.channel).order_by(Sale.id)
    record_number = query.where(Sale.id < sale.id).count()
    return record_number + 1


def delete_sale(sale_id: int) -> None:
    Sale.delete_by_id(sale_id)
