import sys
import os
import requests
from requests.adapters import HTTPAdapter, Retry
import datetime
from datetime import datetime, timedelta
import time
import iso8601
import pytz
import re


def get_bugfender_base_url():
    return "https://dashboard.bugfender.com"


def get_request_session_token():
    return requests.Session()


def make_api_get_request(url, headers, params, helper):
    session = get_request_session_token()
    helper.log_debug(
        f"[>] make_api_get_request() - Querying URL {url} with parameters {params}"
    )

    retry = True
    response = None
    while (retry):
        try:
            response = session.get(url, headers=headers, params=params)
            response.raise_for_status()
        except Exception as e:
            if (response.status_code in [429, 502, 503, 504]):
                helper.log_error(f"Error code {response.status_code} received. Waiting 60 seconds and trying again.")
                time.sleep(60)
                continue
            helper.log_error(f"GET Request to {url} failed: {str(e)}")
            raise e
        helper.log_debug(
            f"[>] make_api_get_request() - Data successfully retrieved from {url}."
        )
        retry = False

    return response.json() if response else None


def get_auth_token_headers(helper):
    helper.log_debug("[>] get_bugfender_auth_token()")
    opt_account = helper.get_arg("bugfender_account")
    opt_client_id = opt_account.get("client_id")
    opt_client_secret = opt_account.get("client_secret")

    url = get_bugfender_base_url() + "/auth/token"
    headers = {"Content-type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": opt_client_id,
        "client_secret": opt_client_secret,
    }
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
    except Exception as e:
        helper.log_error(
            f"POST Request to {url} to obtain access token failed: {str(e)}"
        )
        raise e

    auth_token = response.json().get("access_token")
    return {"Authorization": f"Bearer {auth_token}"}


def get_latest_timestamp(helper):
    lastest_timestamp_checkpoint_key = (
        f"{helper.get_input_stanza_names()}_most_recent_timestamp"
    )
    lastest_timestamp = helper.get_check_point(lastest_timestamp_checkpoint_key)
    helper.log_debug(
        f"[>] get_latest_timestamp() -> latest timestamp received: {lastest_timestamp}"
    )
    return lastest_timestamp


def set_latest_timestamp(timestamp_datetime_object, helper):
    key = f"{helper.get_input_stanza_names()}_most_recent_timestamp"
    timestamp = timestamp_datetime_object.strftime("%Y-%m-%dT%H:%M:%SZ")
    helper.save_check_point(key, timestamp)
    helper.log_debug(
        f"[>] get_latest_timestamp() -> wrote timestamp '{timestamp}' to checkpoint lookup file."
    )


def select_start_date(helper):
    latest_timestamp = get_latest_timestamp(helper)
    if latest_timestamp:
        return latest_timestamp

    initial_start_date = helper.get_arg("initial_start_date")
    if initial_start_date:
        return initial_start_date

    return None


def check_and_update_headers(query_start_time, headers, helper):
    if (
        time.time() - query_start_time > 2700
    ):  # If more than 45 minutes have passed, issue new auth token and reset timer
        helper.log_debug(
            "[>] get_bugfender_devices_endpoint_data() - 45 minutes have passed, acquiring new access token and reset timer."
        )
        return (time.time(), get_auth_token_headers(helper))
    else:
        return (query_start_time, headers)


def get_bugfender_app_list(helper):
    helper.log_debug("[>] get_bugfender_app_list()")
    url = get_bugfender_base_url() + "/api/app"
    headers = get_auth_token_headers(helper)
    return make_api_get_request(url, headers, None, helper)


def get_bugfender_app_devices(helper):
    helper.log_debug("[>] get_bugfender_app_devices()")

    # The /issues endpoint works with pagination, therefore multiple API calls are performed.
    # If the overall process is taking longer than one hour, the access token expires. Therefore,
    # we are tracking the time.
    # query_start_time = time.time()
    # query_start_timestamp = datetime.utcnow()

    app_id = helper.get_arg("app_id")
    url = get_bugfender_base_url() + f"/api/app/{app_id}/devices"
    params = {
        # "date_range_start": select_start_date(helper),
        "format": "json",
        "order": "seen",
        "page_size": "100",
    }
    headers = get_auth_token_headers(helper)

    devices_list = []
    next_cursor = "START"  # intial value to enter while loop below
    while next_cursor and next_cursor != "":
        if next_cursor != "START":
            params["next_cursor"] = next_cursor

        # query_start_time, headers = check_and_update_headers(
        #     query_start_time, headers, helper
        # )
        response = make_api_get_request(url, headers, params, helper)

        devices = response.get("devices")
        if devices:
            devices_list += devices
            helper.log_debug(
                f"Response - Received {len(devices)}. Total devices received so far: {len(devices_list)}"
            )
        next_cursor = response.get("next_cursor")

    # set_latest_timestamp(query_start_timestamp, helper)
    return devices_list


def get_bugfender_app_issues(helper):
    helper.log_debug("[>] get_bugfender_app_issues()")

    # The /issues endpoint works with pagination, therefore multiple API calls are performed.
    # If the overall process is taking longer than one hour, the access token expires. Therefore,
    # we are tracking the time.
    query_start_time = time.time()
    query_start_timestamp = datetime.utcnow()

    app_id = helper.get_arg("app_id")
    url = get_bugfender_base_url() + f"/api/app/{app_id}/issues"

    params = {
        "date_range_start": select_start_date(helper),
        "issue_status": (
            "4" if helper.get_arg("issue_status") == "issue_status_closed" else "1"
        ),
        "page_size": "100",
        "version": "-1",  # This API enpoint is not without issues. We were told to set this parameter to "-1" to make it work by the Bugfender folks.
    }

    # For some reason, the /issues endpoint does NOT accept 'None' as a parameter for 'date_range_start'
    if params.get("date_range_start") is None:
        params["date_range_start"] = datetime(1970, 1, 1, tzinfo=pytz.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

    headers = get_auth_token_headers(helper)

    # setting the amount of total pages to 1, later
    # in the for loop, this value will get updates with
    # the actual total_pages value
    page = 1
    total_pages = 1  # initial value, to be changed inside while loop below
    total_pages_updated = False

    total_issues = []
    while page <= total_pages:
        query_start_time, headers = check_and_update_headers(
            query_start_time, headers, helper
        )
        params["page"] = page

        response = make_api_get_request(url, headers, params, helper)

        if not total_pages_updated:
            total_pages = response.get("total_pages")
            total_pages_updated = True

        # for debugging
        item_count = response.get("item_count")
        page_index = response.get("page_index")
        helper.log_debug(
            f"/issues response - item_count: {item_count}, page_index: {page_index}, total_pages: {total_pages}"
        )

        issues = response.get("issues")
        total_issues += issues
        page += 1

    set_latest_timestamp(query_start_timestamp, helper)
    return total_issues


def get_bugfender_app_logs(helper):
    helper.log_debug("[>] get_bugfender_app_logs()")

    # The /logs endpoint works with pagination, therefore multiple API calls are performed.
    # If the overall process is taking longer than one hour, the access token expires. Therefore,
    # we are tracking the time.
    query_start_time = time.time()
    query_start_timestamp = datetime.utcnow()

    app_id = helper.get_arg("app_id")
    url = get_bugfender_base_url() + f"/api/app/{app_id}/logs/paginated"
    params = {"date_range_start": select_start_date(helper), "page_size": 10000}
    headers = get_auth_token_headers(helper)

    # We call the API one time to receive the URL to the latest event, then
    # we will continuosly query all previous events
    first_call_data = make_api_get_request(url, headers, params, helper)
    url = first_call_data.get("last")

    log_list = []
    while url is not None:
        query_start_time, headers = check_and_update_headers(
            query_start_time, headers, helper
        )
        response = make_api_get_request(url, headers, None, helper)

        if response.get("data"):
            log_list += response.get("data")

        url = response.get("previous")

    set_latest_timestamp(query_start_timestamp, helper)
    return log_list


def validate_initial_start_date(start_date):
    regex = r"(\d{4}-\d{2}-\d{2})[A-Z]+(\d{2}:\d{2}:\d{2}Z)"
    match = re.compile(regex).match
    if match(start_date) is None:
        raise ValueError(
            "Start date and end date have to be in ISO8601 format YYYY-MM-DDThh:mm:ssZ (e.g. 2023-08-25T12:35:00Z)"
        )


# code stolen from here: https://stackoverflow.com/questions/62764701/how-to-validate-that-a-string-is-a-time-in-rfc3339-format
def validate_rfc3339(date):
    if date is None:
        return
    try:
        assert datetime.strptime(date, "%Y-%m-%dT%H:%M:%S%z").tzinfo is not None
    except ValueError:
        raise ValueError("Incorrect data format, time should be YYYY-MM-DDThh:mm:ss:z")


# timestamp conversion. Based on: https://medium.com/@pritishmishra_72667/converting-rfc3339-timestamp-to-utc-timestamp-in-python-8dfa485358ff
def convert_rfc3339_to_utc(rfc333_date, helper):
    try:
        date_obj = iso8601.parse_date(rfc333_date)
        date_utc = date_obj.astimezone(pytz.utc)
    except Exception as e:
        helper.log_error(
            f"Something went wrong during timestamp conversion from rfc3339 to utc: {str(e)}"
        )
        raise e
    return date_utc


def convert_datetime_to_rfc3339_and_add_second(utc_date, helper):
    try:
        date_obj = iso8601.parse_date(utc_date)
        date_obj = (date_obj + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        helper.log_debug(
            f"Retreived date converted to {date_obj}, with one second being added."
        )
    except Exception as e:
        helper.log_error(
            f"Something went wrong during timestamp conversion from datetime object to rfc3339 string: {str(e)}"
        )
        raise e
    return date_obj


# timestamp conversion. Based on: https://medium.com/@pritishmishra_72667/converting-rfc3339-timestamp-to-utc-timestamp-in-python-8dfa485358ff
def convert_rfc3339_to_utc_total_seconds(rfc333_date, helper):
    try:
        date_obj = iso8601.parse_date(rfc333_date)
        date_utc = date_obj.astimezone(pytz.utc)
        delta = date_utc - datetime(1970, 1, 1, tzinfo=pytz.utc)
    except Exception as e:
        helper.log_error(
            f"Something went wrong during timestamp conversion from rfc3339 to utc: {str(e)}"
        )
        raise e
    return delta.total_seconds()
