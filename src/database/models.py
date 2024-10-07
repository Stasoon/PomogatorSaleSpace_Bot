from datetime import datetime
from peewee import (
    Model, PostgresqlDatabase, SqliteDatabase, AutoField,
    SmallIntegerField, BigIntegerField, IntegerField,
    DateTimeField, CharField, DecimalField, BooleanField,
    ForeignKeyField
)


db = SqliteDatabase(
    database='data.db'
    # DatabaseConfig.NAME,
    # user=DatabaseConfig.USER, password=DatabaseConfig.PASSWORD,
    # host=DatabaseConfig.HOST, port=DatabaseConfig.PORT
)


class _BaseModel(Model):
    class Meta:
        database = db


class User(_BaseModel):
    """ Пользователь бота """
    class Meta:
        db_table = 'users'

    telegram_id = BigIntegerField(primary_key=True, unique=True, null=False)
    name = CharField(default='Пользователь')
    username = CharField(null=True, default='Пользователь')
    last_activity = DateTimeField(null=True)
    bot_blocked = BooleanField(default=False)
    registration_timestamp = DateTimeField()

    def __str__(self):
        return f"@{self.username}" if self.username else f"tg://user?id={self.telegram_id}"


class Channel(_BaseModel):
    class Meta:
        db_table = 'channels'

    id = BigIntegerField(primary_key=True)
    creator = ForeignKeyField(User)
    title = CharField(max_length=350)
    secret_code = CharField(max_length=50)
    table_id = CharField(null=True)

    def __str__(self):
        return self.title


class ChannelWriter(_BaseModel):
    class Meta:
        db_table = 'users_channels'

    user = ForeignKeyField(User)
    channel = ForeignKeyField(Channel)


class Sale(_BaseModel):
    class Meta:
        db_table = 'sales'

    id = AutoField()

    writer = ForeignKeyField(User)
    channel = ForeignKeyField(Channel)

    buyer = CharField(max_length=500)
    publication_cost = DecimalField(max_digits=15, decimal_places=2)
    manager_percent = DecimalField(max_digits=5, decimal_places=2)
    payment_status = CharField(max_length=50)

    publication_format = CharField(max_length=50)
    timestamp = DateTimeField(default=datetime.utcnow)

    def get_date_str(self) -> str:
        return self.timestamp.strftime("%d.%m.%Y")

    def get_time_str(self) -> str:
        return self.timestamp.strftime("%H:%M")


class SalePaymentsReminder(_BaseModel):
    class Meta:
        db_table = 'sale_payments_reminders'

    id = AutoField()
    sale = ForeignKeyField(Sale)
    reminder_time = DateTimeField()


class Admin(_BaseModel):
    """ Администратор бота """
    class Meta:
        db_table = 'admins'

    telegram_id = BigIntegerField(unique=True, null=False)
    name = CharField()


def register_models() -> None:
    for model in _BaseModel.__subclasses__():
        model.create_table()
