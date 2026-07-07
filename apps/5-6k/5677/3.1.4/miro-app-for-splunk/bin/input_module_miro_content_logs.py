
# encoding = utf-8

import datetime
import json
from datetime import timezone

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
DATETIME_API_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
DATETIME_CHECKPOINT_VALID_FORMATS = (DATETIME_API_FORMAT, "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%MZ")
PAGE_LIMIT = 500
# replace to local address for easy testing
CONTENT_LOGS_ENDPOINT = 'https://api.miro.com/v2/orgs/{}/content-logs/items'


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
    organization_id = helper.get_arg("organization_id")
    date_from = get_start_time(helper)
    utc_now = get_utc_now_in_api_format()
    date_to = utc_now
    initial_parameters = {
        "from": date_from,
        "to": date_to,
        "limit": PAGE_LIMIT,
        "sortDirection": "ASC"
    }
    total_new_events_count = 0
    url = CONTENT_LOGS_ENDPOINT.format(organization_id)

    log_debug(helper, "Start collecting miro content logs from {} to {}.".format(date_from, date_to))
    result = get_content_logs(helper, url, access_token, initial_parameters)
    content_logs = result.get("data", [])
    cursor = result.get("cursor")
    returned_size = result.get("size")

    if returned_size:
        total_new_events_count += create_content_logs_events(helper, event_writer, content_logs)

    log_debug(helper, "Initial cursor & size are {} & {}.".format(cursor, returned_size))
    log_debug(
        helper,
        "Show first miro content log after collecting from {} to {}: {}".format(
            date_from, date_to, content_logs
        )
    )

    while returned_size and len(cursor) > 0:
        next_parameters = initial_parameters.copy()
        # update cursor for the next page
        next_parameters.update({
            "cursor": cursor
        })
        result = get_content_logs(helper, url, access_token, next_parameters)
        content_logs = result.get("data", [])
        cursor = result.get("cursor")
        returned_size = result.get("size")

        if returned_size:
            total_new_events_count += create_content_logs_events(helper, event_writer, content_logs)

        log_debug(helper, "Next cursor is {}.".format(cursor))
        log_debug(
            helper,
            "Show next miro content log after collecting from {} to {}: {}".format(
                date_from, date_to, content_logs
            )
        )

    # use date_to as next start time
    save_next_start_time(helper, date_to)
    log_info(
        helper,
        "Finished collecting miro content logs from {} to {}. Total events created: {}".format(
            date_from, date_to, total_new_events_count
        )
    )

    return total_new_events_count


class ResponseNotOkException(Exception):
    def __init__(self, response):
        self.response = response
        self.message = u'%s Status Code: %s for url: %s' % (response.status_code, response.reason, response.url)
        super().__init__(self.message)

def get_content_logs(helper, url, access_token, parameters=None):
    log_debug(helper, "Get content logs from url {}".format(url))
    headers = {
        "Accept": "application/json",
        "Authorization": "Bearer {}".format(access_token),
        "User-Agent": "MiroAppForSplunk/{}".format(VERSION),
        # for local testing, since passport is not propagated by gateway in local env
        #"X-MIRO-ID": "..."
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

def create_content_logs_events(helper, event_writer, content_logs):
    # We request content logs sorted by 'actionTime' date ASC
    # so we can mark the latest successful 'actionTime' as the next start time
    for event_data in content_logs:
        event = helper.new_event(
            data=json.dumps(event_data),
            index=helper.get_output_index(),
            source=helper.get_input_type(),
            sourcetype=helper.get_sourcetype()
        )
        event_writer.write_event(event)
        next_start_time = event_data.get("actionTime")
        save_next_start_time(helper, next_start_time)

    new_events_count = len(content_logs)
    log_debug(helper, "Created {} new events.".format(new_events_count))
    return new_events_count

def convert_to_api_datetime_format(date):
    """
    Converts date to iso format without microseconds and with a trailing "Z".
    :param date: datetime object.
    :return: string date in api allowed format.
    """
    return date.strftime(DATETIME_API_FORMAT)


def get_utc_now_in_api_format():
    return convert_to_api_datetime_format(datetime.datetime.now(timezone.utc))


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
        utc_now_minus_interval = datetime.datetime.now(timezone.utc) - datetime.timedelta(seconds=interval)
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
