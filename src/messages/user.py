from src.database.models import Sale, User


class UserMessages:
    # Ресурсы: https://telegra.ph/Pomogator-google-resources-02-20

    @staticmethod
    def get_loading_animation() -> str:
        return 'https://telegra.ph/file/95c7d294b3f44d56e7048.mp4'

    @staticmethod
    def get_month_name(month_num: int) -> str:
        names = [
            '', 'январь', 'февраль', 'март', 'апрель',
            'май', 'июнь', 'июль', 'август', 'сентябрь',
            'октябрь', 'ноябрь', 'декабрь'
        ]
        return names[month_num]

    @staticmethod
    def get_welcome_photo() -> str:
        return 'https://telegra.ph/file/d4204af9476630c8da03e.png'

    @staticmethod
    def get_welcome(user_name: str) -> str:
        return (
            f'🤝 <b>Привет!</b> Я космический помощник учета проданных рекламных мест. \n\n'
            f'Для начала советую подписаться: \n\n'
            
            '1. <a href="https://t.me/telegagroups">Блог Telegramщики</a> \n'
            '2. <a href="https://t.me/+SJ5iV_8cNGtkYTNi">Чат для админов</a> \n\n'
            
            '<b>А теперь вводи нужную информацию 🔍</b>'
        )

    @staticmethod
    def get_main_menu() -> str:
        return 'Меню:'

    @staticmethod
    def get_my_channels() -> str:
        return ' 📢 Ваши каналы:'

    @staticmethod
    def get_bot_not_added_to_channel_error_retry() -> str:
        return 'Вы не добавили бота в канал! \n\nДобавьте бота в канал и перешлите сюда пост:'

    @staticmethod
    def get_channel_already_added_error() -> str:
        return 'Вы уже добавляли этот канал!'

    @staticmethod
    def get_channel_added() -> str:
        return '✅ Канал добавлен'

    @staticmethod
    def get_create_purchase() -> str:
        return 'Создание продажи'

    @classmethod
    def get_channel_profit(cls, channel_title: str, month_profit: float, manager_profit: float, month_num: int) -> str:
        return (
            f"<b>📄 Отчет продаж за {cls.get_month_name(month_num)} </b> \n\n"
            f"Доход: {month_profit:.2f} <b>₽</b> \n"
            f"Доход менеджера за месяц: {manager_profit:.2f} <b>₽</b> \n"
        )

    @staticmethod
    def get_user_not_channel_writer_error() -> str:
        return '❌ Вы не являетесь редактором этого канала'

    @staticmethod
    def ask_for_publication_date() -> str:
        return f'⏰ Дата публикации:'

    @staticmethod
    def get_purchase_notification_for_owner(publisher: User, purchase: Sale):
        if publisher.username:
            publisher_name = f'@{publisher.username}'
        else:
            publisher_name = f'<a href="tg://user?id={publisher.telegram_id}">{publisher.name}</a>'

        return (
            "📄 Новый отчет \n\n"
            f"Менеджер: {publisher_name} \n"
            f"Дата: {purchase.timestamp.strftime('%d.%m')} \n"
            f"Время: {purchase.timestamp.strftime('%H:%M')} \n"
            f"Цена рекламного места: {purchase.publication_cost} ₽ \n"
            f"Формат: {purchase.publication_format}"
        )

    @staticmethod
    def get_not_enough_rights() -> str:
        return 'У вас нет прав для совершения этой операции!'

    @staticmethod
    def get_unknown_command() -> str:
        return '❓ Команда не распознана. \n\nПожалуйста, пользуйтесь клавиатурой:'

    @staticmethod
    def get_add_channels_first() -> str:
        return 'Сначала создайте вашу первую продажу!'
