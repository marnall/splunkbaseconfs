# encoding = utf-8

import datetime
import json

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''

VERSION = "3.1.4"
NEXT_START_TIME_KEY = 'next_start_time'
DATETIME_FORMAT_RETURNED_BY_API = "%Y-%m-%dT%H:%M:%S.%f+0000"
DATETIME_API_CALL_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
DATETIME_CHECKPOINT_VALID_FORMATS = (DATETIME_API_CALL_FORMAT + "Z", "%Y-%m-%dT%H:%MZ")
PAGE_LIMIT = 500
AUDIT_LOGS_ENDPOINT = 'https://api.miro.com/v2/audit/logs'


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    pass


def collect_events(helper, event_writer):
    """
    Collect events and stream to Splunk using event writer provided.
    :param helper: A `BaseModInput` object.
    :param event_writer: An object with methods to write events and log messages to Splunk.
    :return: count of total events created.
    """

    access_token = helper.get_arg("access_token")
    created_after = get_start_time(helper)
    utc_now = get_utc_now_in_api_format()
    created_before = utc_now
    initial_parameters = {
        "createdAfter": created_after,
        "createdBefore": created_before,
        "limit": PAGE_LIMIT,
    }
    total_new_events_count = 0
    url = AUDIT_LOGS_ENDPOINT

    log_debug(helper, "Start collecting miro audit logs from {} to {}.".format(created_after, created_before))
    result = get_audit_logs(helper, url, access_token, initial_parameters)
    audit_logs = result.get("data", [])
    cursor = result.get("cursor")
    size = result.get("size")

    if size:
        total_new_events_count += create_audit_logs_events(helper, event_writer, audit_logs)

    log_debug(helper, "Initial cursor & size are {} & {}.".format(cursor, size))
    log_debug(
        helper,
        "Show first miro audit log after collecting from {} to {}: {}".format(
            created_after, created_before, audit_logs
        )
    )

    while size and cursor:
        next_parameters = initial_parameters.copy()
        next_parameters.update({
            "cursor": cursor
        })
        result = get_audit_logs(helper, url, access_token, next_parameters)
        # update size & cursor for the next page
        audit_logs = result.get("data", [])
        cursor = result.get("cursor")
        size = result.get("size")

        if size:
            total_new_events_count += create_audit_logs_events(helper, event_writer, audit_logs)

        log_debug(helper, "Next cursor & size are {} & {}.".format(cursor, size))
        log_debug(
            helper,
            "Show next miro audit log after collecting from {} to {}: {}".format(
                created_after, created_before, audit_logs
            )
        )

    # use current created_before date as next start time
    save_next_start_time(helper, created_before)
    log_info(
        helper,
        "Finish collecting miro audit logs from {} to {}. Total events created: {}".format(
            created_after, created_before, total_new_events_count
        )
    )

    return total_new_events_count


class ResponseNotOkException(Exception):
    def __init__(self, response):
        self.response = response
        self.message = u'%s Status Code: %s for url: %s' % (response.status_code, response.reason, response.url)
        super().__init__(self.message)

def get_audit_logs(helper, url, access_token, parameters=None):
    log_debug(helper, "Get audit logs from url {}".format(url))
    headers = {
        "Accept": "application/json",
        "Authorization": "Bearer {}".format(access_token),
        "User-Agent": "MiroAppForSplunk/{}".format(VERSION)
    }
    method = "GET"
    response = helper.send_http_request(
        url=url,
        method=method,
        parameters=parameters,
        headers=headers,
        payload=None,
        cookies=None,
        verify=True,
        cert=None,
        timeout=None,
        use_proxy=True
    )

    if response.status_code != 200:
        error = ResponseNotOkException(response)
        log_error(helper, str(error))
        raise error

    return response.json()


def create_audit_logs_events(helper, event_writer, audit_logs):
    # Audit logs are sorted by 'createdAt' date DESC and we need them sorted ASC
    # so we can mark the latest successful 'createdAt' as the next start time
    for event_data in audit_logs:
        event = helper.new_event(
            data=json.dumps(event_data),
            index=helper.get_output_index(),
            source=helper.get_input_type(),
            sourcetype=helper.get_sourcetype()
        )
        event_writer.write_event(event)
        next_start_time = convert_created_at_to_next_start_time(event_data.get("createdAt"))
        save_next_start_time(helper, next_start_time)

    new_events_count = len(audit_logs)
    log_debug(helper, "Created {} new events.".format(new_events_count))
    return new_events_count


def convert_created_at_to_next_start_time(created_at):
    """
    Converts audit logs event 'createdAt' date format to a valid format to be used as query parameter.

    :param created_at: createdAt date in `DATETIME_FORMAT_RETURNED_BY_API` format.
    :return: next start time in api datetime format.
    """
    event_created_at_time = datetime.datetime.strptime(created_at, DATETIME_FORMAT_RETURNED_BY_API)
    # Add a microsecond so next start time does not include the last event created
    next_start_time = event_created_at_time + datetime.timedelta(milliseconds=1)
    return convert_to_api_datetime_format(next_start_time)


def convert_to_api_datetime_format(date):
    """
    Converts date to iso format without microseconds and with a trailing "Z".
    :param date: datetime object.
    :return: string date in api allowed format.
    """
    return date.strftime(DATETIME_API_CALL_FORMAT)[:-3] + "Z"


def get_utc_now_in_api_format():
    return convert_to_api_datetime_format(datetime.datetime.utcnow())


def get_next_start_time(helper):
    cursor_key = _get_check_point_key(helper, NEXT_START_TIME_KEY)
    return helper.get_check_point(cursor_key)

def get_next_start_time_datetime(helper, next_start_time):
    for fmt in DATETIME_CHECKPOINT_VALID_FORMATS:
        try:
            return datetime.datetime.strptime(next_start_time, fmt)
        except ValueError:
            pass
    log_error(helper, "Checkpoint wrong format: {}".format(next_start_time))


def save_next_start_time(helper, next_start_time):
    check_point_key = _get_check_point_key(helper, NEXT_START_TIME_KEY)
    helper.save_check_point(key=check_point_key, state=next_start_time)


def _get_check_point_key(helper, key):
    input_name = helper.get_input_stanza_names()
    checkpoint_key = "{}_{}".format(input_name, key)
    return checkpoint_key


def get_start_time(helper):
    next_start_time = get_next_start_time(helper)

    if next_start_time:
        log_debug(helper, "Checkpoint '{}' found. Start time is {}".format(NEXT_START_TIME_KEY, next_start_time))
        next_start_time_datetime = get_next_start_time_datetime(helper, next_start_time)
        return convert_to_api_datetime_format(next_start_time_datetime)
    else:
        # For the first start time pull data from "now" minus "interval" in UTC
        interval = int(helper.get_arg("interval"))
        utc_now_minus_interval = datetime.datetime.utcnow() - datetime.timedelta(seconds=interval)
        start_time = convert_to_api_datetime_format(utc_now_minus_interval)
        log_debug(helper, "Checkpoint '{}' NOT found. Start time is {}".format(NEXT_START_TIME_KEY, start_time))
        return start_time


def log_debug(helper, msg):
    helper.log_debug(_log_message(helper, msg))


def log_info(helper, msg):
    helper.log_info(_log_message(helper, msg))


def log_error(helper, msg):
    helper.log_error(_log_message(helper, msg))


def _log_message(helper, msg):
    input_name = helper.get_input_stanza_names()
    message = "%s | %s" % (input_name, str(msg))
    return message
