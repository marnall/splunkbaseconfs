from functools import reduce


def format_date_string(date_string):
    """Formats a date string into YYYY-MM-DD HH:mm:ss format.

    :param date_string: str
    :return: str
    """
    # :FIXME: python-dateutil is a better option for formatting
    return date_string.replace('T', ' ')[:19]


def dict_to_kv_string(data):
    """Converts a dictionary to key=value string.

    :param data: dict
    :return: str
    """
    return reduce(
        lambda acc, val: "{} {}={}".format(acc, val[0], val[1]),
        data.items(),
        '',
    ).strip()


def get_check_point_name(domain, obj_type):
    """
    Forming and returning checkpoint names.

    :param domain: company name
    :param obj_type: different objects eg.overall, issue etc.
    :return: checkpoint name
    """
    return '{}_LastRunDate1_{}'.format(domain, obj_type)
