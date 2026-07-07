import time
import datetime


one_day_ms = 86400000
one_day_s = 86400
one_hour_ms = 3600000
one_hour_s = 3600


def get_utc_now():
    return datetime.datetime.utcnow()


def get_utc_now_datetime_string():
    return get_utc_now().strftime('%Y-%m-%d %H:%M:%S')


def get_epoch_ms():
    return int(time.time() * 1000)


def get_epoch_s():
    return int(round(time.time()))


def thirty_days_back_epoch_ms():
    now = get_epoch_ms()
    thirty_days_ms = one_day_ms * 30
    return now - thirty_days_ms


def thirty_days_back_epoch():
    now = get_epoch_s()
    thirty_days = one_day_s * 30
    return now - thirty_days


def twenty_four_hours_from_timestamp_epoch_ms(timestamp):
    return timestamp + one_day_ms


def twenty_four_hours_from_timestamp_epoch(timestamp):
    return timestamp + one_day_s


def one_hour_from_timestamp_epoch_ms(timestamp):
    return timestamp + one_hour_ms


def one_day_before_now_epoch_ms():
    return get_epoch_ms() - one_day_ms


def one_day_before_now_epoch_s():
    return get_epoch_s() - one_day_s 
