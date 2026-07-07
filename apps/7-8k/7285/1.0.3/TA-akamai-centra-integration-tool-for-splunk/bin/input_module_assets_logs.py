# encoding = utf-8
import json
import traceback
from datetime import datetime, timedelta

# Constants
BATCH_SIZE = 1000

# Default days to backtrack if no start date or checkpoint
DEFAULT_BACKTRACK_DAYS = 365
def validate_input(helper, definition):
    """Implement validation logic for input configurations."""
    pass

def collect_events(helper, ew):
    token = _get_token(helper)
    if token:
        helper.log_info("Connected to management server successfully.")
        headers = {"Authorization": "Bearer {}".format(token)}
        try:
            collect_asset_logs(helper, ew, headers)
        except Exception as e:
            helper.log_error(f"Error running collect_asset_logs: {e}")
            helper.log_error(traceback.format_exc())
        finally:
            _logout(helper, headers)
    else:
        helper.log_error("Error connecting to management server.")

def collect_asset_logs(helper, ew, headers):
    helper.log_debug("Starting to collect asset logs.")
    from_time, to_time = _get_timestamps("prev_timestamp_asset_logs", helper)
    helper.save_check_point("prev_timestamp_asset_logs", to_time)
    parameters = {"report_time": f"{from_time},{to_time}"}
    total_count = _get_data(helper, "assets-log", headers=headers,
                            parameters=parameters).get("total_count", 0)
    helper.log_debug(f"Found {total_count} new asset logs.")
    processed_events = 0
    while processed_events < total_count:
        parameters.update({"offset": processed_events, "limit": BATCH_SIZE})
        assets = _get_data(helper, "assets-log", headers=headers,
                           parameters=parameters).get("objects", [])
        for asset in assets:
            asset["data_type"] = "assets_log"
            _process_and_write_asset(helper, ew, asset)
        processed_events += len(assets)
    helper.log_debug("Finished collecting asset logs.")

def _get_timestamps(key, helper):
    start_date = helper.get_arg("start_date")
    from_time = helper.get_check_point(key)
    if not start_date and not from_time:
        from_time = helper.get_check_point(key) or _to_timestamp_str(
            datetime.utcnow() - timedelta(days=DEFAULT_BACKTRACK_DAYS))
    if start_date and not from_time:
        from_time = _to_timestamp_str(
            datetime.strptime(start_date, "%Y/%m/%d"))
    to_time = _to_timestamp_str(datetime.utcnow())
    return from_time, to_time

def _process_and_write_asset(helper, ew, data):
    data["host"] = helper.get_arg("environment_host")
    timestamp = float(data["report_time"]) / 1000
    data["report_date"] = str(datetime.fromtimestamp(timestamp))
    event_data = json.dumps(data)
    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(),
                             sourcetype=helper.get_sourcetype(), time=timestamp, data=event_data)
    ew.write_event(event)

def _get_data(helper, endpoint, method="GET", parameters=None, headers=None, payload=None):
    headers = headers or {}
    
    if method == "POST":
        headers["Content-Type"] = "application/json"
    host, port, timeout, verify_ssl = _get_connection_details(helper)
    url = f"https://{host}:{port}/api/v3.0/{endpoint}"
    
    try:
        response = helper.send_http_request(url, method, headers=headers, parameters=parameters,
                                            payload=payload, use_proxy=True, verify=verify_ssl, timeout=timeout)
        if response.status_code == 200:
            return response.json()
        else:
            helper.log_error(
                f"Received response {response.status_code} for endpoint {endpoint}: {response.text}")
            return {}
    except ValueError:
        return response.text
    except Exception as e:
        helper.log_critical("Failed getting data from REST API")
        helper.log_error(str(e))
        return {}
    
def _get_token(helper):
    """Authenticate and return the access token."""
    global_account = helper.get_arg('guardicore_api_account')
    username = global_account['username']
    password = global_account['password']
    payload = {"username": username, "password": password}
    response = _get_data(helper, "authenticate",
                         method="POST", payload=payload)
    return response.get("access_token")

def _logout(helper, headers):
    """Log out from the API."""
    return _get_data(helper, "logout", method="POST", headers=headers)

def _to_timestamp_str(dt):
    """Convert a datetime object to a string representation of its timestamp."""
    return str(int(dt.timestamp() * 1000))

def _get_connection_details(helper):
    """Retrieve connection details from the modular input configuration."""
    host = helper.get_arg("environment_host")
    port = helper.get_arg("port") or "443"
    timeout = int(helper.get_arg("request_timeout") or "30")
    verify_ssl = bool(helper.get_arg("verify_requests"))
    return host, port, timeout, verify_ssl
