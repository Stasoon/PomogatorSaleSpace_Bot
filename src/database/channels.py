import secrets
import string

from .models import Channel, User, ChannelWriter


def __generate_secret_code(length: int = 15) -> str:
    alphabet = string.ascii_letters + string.digits
    secret_code = ''.join(secrets.choice(alphabet) for _ in range(length))
    return secret_code


def create_channel(creator: User, channel_title: str, table_url: str = None) -> Channel | None:
    channel = get_channel_by_title(title=channel_title)

    if channel:
        return None

    secret_code = __generate_secret_code()
    while get_channel_by_secret_code(secret_code):
        secret_code = __generate_secret_code()

    channel = Channel.create(creator=creator, title=channel_title, secret_code=secret_code, table_url=table_url)
    ChannelWriter.create(user=creator, channel=channel)
    return channel


def add_writer_to_channel(user: User, channel: Channel):
    return ChannelWriter.get_or_create(user=user, channel=channel)


def update_channel_secret_code(channel: Channel):
    secret_code = __generate_secret_code()
    while get_channel_by_secret_code(secret_code):
        secret_code = __generate_secret_code()

    channel.secret_code = secret_code
    channel.save()
    return channel


def get_channel_by_title(title: str) -> Channel | None:
    return Channel.get_or_none(title=title)


def get_channel_by_secret_code(code: str) -> Channel | None:
    return Channel.get_or_none(secret_code=code)


def get_channel_by_id(channel_id: int) -> Channel | None:
    return Channel.get_or_none(id=channel_id)


def get_user_channels(user: User | int) -> list[Channel]:
    query = (
        Channel
        .select()
        .join(ChannelWriter)
        .where(ChannelWriter.user == user)
    )

    return list(query)


def is_user_channel_writer(user: User | int, channel: Channel | int) -> bool:
    return channel.creator == user or ChannelWriter.get_or_none(user=user, channel=channel)
