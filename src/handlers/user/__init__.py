from aiogram import Router

from .start_command import register_menu_handlers
from .create_sale import register_purchases_handlers
from .total_profit import register_total_profit_handlers
from .sales_calendar import register_sales_calendar_handlers
from .channels import register_channels_handlers
from .unknown_messages import register_unknown_messages_handler


def register_user_handlers(router: Router):
    register_menu_handlers(router)
    register_sales_calendar_handlers(router)
    register_purchases_handlers(router)
    register_total_profit_handlers(router)
    register_channels_handlers(router)

    register_unknown_messages_handler(router)
