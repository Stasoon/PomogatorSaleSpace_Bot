from enum import Enum


class SalePaymentStatusEnum(str, Enum):
    PAID = "Оплачено"
    BOOKED = "Забронировано"
    BY_SPM = "По СПМ"
