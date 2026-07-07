import os
import sys
import requests
from requests.adapters import HTTPAdapter, Retry
import re
from datetime import datetime
from dateutil import tz
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import pytz

def validate_dates(start_date, end_date, day_threshold):
    regex = r'(\d{4}-\d{2}-\d{2})[A-Z]+(\d{2}:\d{2}Z)'
    match = re.compile(regex).match
    if(match(start_date) is None or match(end_date) is None):
        raise ValueError("Start date and end date have to be in ISO8601 format YYYY-MM-DDThh:mmZ (e.g. 2023-08-25T12:35Z)")
    
    dt_start_date = datetime.strptime(start_date, "%Y-%m-%dT%H:%MZ")
    dt_end_date = datetime.strptime(end_date, "%Y-%m-%dT%H:%MZ")
    if((dt_end_date - dt_start_date).days > day_threshold):
        raise ValueError(f"The date range you have specified is greater than {day_threshold} days. Please select a smaller date range.")

def get_time_now_seconds():
    return (datetime.now().replace(tzinfo=pytz.utc) - datetime(1970, 1, 1, tzinfo=pytz.utc)).total_seconds()

def get_request_session_token():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=60, status_forcelist=[ 502, 503, 50, 429 ])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

def make_api_call(url, params, headers, continue_after_failure, helper):
    helper.log_debug(f"Performing API call to Url {url} and params: {params}")
    session = get_request_session_token()
    try:
        response = session.get(url, params=params, headers=headers)
        response.raise_for_status()
    except Exception as e:
        helper.log_error(f"Could not import data due to following error: {e}. Error experienced during API call with url={url} and params={params}. Skipping: {continue_after_failure}")
        if (not continue_after_failure):
            raise(e)
        else:
            return None
    helper.log_debug(f"Response successfully received form {url} (querried with params: {params}).")
    return response.json()

def electricity_maps_response_is_valid(data, helper):
    error = data.get("error")
    if(error is not None):
        helper.log_error(f"Error in Electricity Maps API response: {str(error)}. This event will not be indexed for Splunk.")
        return False
    message = data.get("message")
    if(message is not None):
        helper.log_error(f"Error in Electricity Maps API response: {str(message)}. This event will not be indexed for Splunk.")
        return False
    return True

def validate_electricity_maps_base_url(url, helper):
    if (url.endswith("/")):
        helper.log_debug(f"[>] electricity_maps_base_url_is_valid() - removing trailing '/' character.")
        return url.rstrip(url[-1])
    return url

def ng_convert_event_timestamp_to_total_seconds(time_string, helper):
    helper.log_debug(f"Converting string {time_string} from National Grid event to total seconds.")
    date_obj = datetime.strptime(time_string, "%Y-%m-%dT%H:%M%z").replace(tzinfo=tz.gettz('UTC'))
    return date_obj.timestamp()

def em_convert_event_timestamp_to_total_seconds(time_string, helper):
    helper.log_debug(f"Converting string {time_string} from Electricity Maps to total seconds.")
    date_obj = datetime.strptime(time_string, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=tz.gettz('UTC'))
    return date_obj.timestamp()

def write_event_to_splunk(ew, event_to_write, timestamp, helper):
    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), time=timestamp, sourcetype=helper.get_sourcetype(), data=event_to_write)
    ew.write_event(event)
    helper.log_debug(f"Event {event_to_write} successfully written to Splunk index '{helper.get_output_index()}'.")