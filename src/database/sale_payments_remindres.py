from datetime import datetime

from .models import Sale, SalePaymentsReminder


def create_sale_payment_reminder(sale_id: int, reminder_time=datetime) -> SalePaymentsReminder:
    return SalePaymentsReminder.create(sale_id=sale_id, reminder_time=reminder_time)
