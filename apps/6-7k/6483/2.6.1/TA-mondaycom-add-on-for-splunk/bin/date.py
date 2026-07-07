from datetime import datetime, timedelta, timezone


def now():
    return format_date(datetime.now(timezone.utc))


def past_hour_date():
    last_hour_date_time = datetime.now(timezone.utc) - timedelta(hours=1)
    return format_date(last_hour_date_time)


def two_weeks_ago():
    last_two_weeks_date_time = datetime.now(timezone.utc) - timedelta(weeks=2)
    return format_date(last_two_weeks_date_time)


def format_date(date):
    return date.strftime('%Y-%m-%dT%H:%M:%S.000Z')
