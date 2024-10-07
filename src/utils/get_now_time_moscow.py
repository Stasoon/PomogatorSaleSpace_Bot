from datetime import datetime, timezone, timedelta


def get_now_time_moscow() -> datetime:
    """ Returns datetime.now() in Moscow """
    msk_timezone = timezone(timedelta(hours=3))
    return datetime.now(msk_timezone)
