import asyncio
from datetime import datetime, timedelta

from loguru import logger

from src.create_bot import bot
from src.database.models import SalePaymentsReminder
from src.keyboards.user import UserKeyboards
from src.misc.enums import SalePaymentStatusEnum


async def send_sale_reminder():
    reminders = (
        SalePaymentsReminder.select()
        .where(
            SalePaymentsReminder.reminder_time >= datetime.now() - timedelta(seconds=40),
            SalePaymentsReminder.reminder_time <= datetime.now() + timedelta(seconds=40)
        )
    )

    completed_reminders_ids = []
    for reminder in reminders:
        sale = reminder.sale
        if sale.payment_status == SalePaymentStatusEnum.BY_SPM.value:
            reminder_text = "Напоминаем, что проходят 24 часа. Посчитайте стоимость."
        else:
            reminder_text = "Бронь не оплатили"
        markup = UserKeyboards.get_open_sale(sale=sale)

        try:
            await bot.send_message(chat_id=sale.writer.telegram_id, text=reminder_text, reply_markup=markup)
        except Exception as e:
            logger.error(e)

        completed_reminders_ids.append(reminder.id)
        await asyncio.sleep(0.05)

    SalePaymentsReminder.delete().where(SalePaymentsReminder.id.in_(completed_reminders_ids)).execute()
