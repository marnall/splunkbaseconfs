# encoding = utf-8
import json
import requests

from constants import VERIFY_REQUESTS, DEFAULT_BACKTRACK_DAYS
from datetime import datetime, timedelta, timezone
from logger import Logger, LogLevel

__author__ = 'Alberto'

class GuardicoreHelper:
    """A class for Guardicore helper functions."""
    def __init__(self, helper, ew):
        self.helper = helper
        self.ew = ew
        self.log = Logger(helper).log
        self.headers = {}
        self.mgmt_server = helper.get_arg("guardicore_management_server")
        self.global_port = helper.get_arg("port")
        self.mgmt_api_uri_v3 = "https://{}:{}/api/v3.0".format(self.mgmt_server, self.global_port)
        self.mgmt_api_uri_v4 = "https://{}:{}/api/v4.0".format(self.mgmt_server, self.global_port)
        self.timeout = int(helper.get_arg("request_timeout"))
        self.log_export_delay = int(self.helper.get_arg("log_export_delay"))

    def to_timestamp_str(self, dt):
        """Convert a datetime object to a string representation of its timestamp."""
        return str(int(dt.timestamp() * 1000))

    def request(self, endpoint, method="GET", parameters=None, payload=None, api_v4=False, raw_response=False):
        """Requests data from the Guardicore management server."""
        # Construct the URL based on the API version
        base_url = self.mgmt_api_uri_v4 if api_v4 else self.mgmt_api_uri_v3
        url = f"{base_url}/{endpoint}"

        # Set headers based on method and response type
        if method == "POST" or raw_response:
            self.headers.update({"Content-Type": "application/json"})

        try:
            # Choose streaming or regular request
            if raw_response:
                new_token = self.get_token()
                self.headers.update({"Authorization": f"Bearer {new_token}"})
                response = requests.get(url, headers=self.headers, verify=VERIFY_REQUESTS, timeout=self.timeout,
                                        stream=True, proxies=self.helper.get_arg("use_proxy"))
            else:
                response = self.helper.send_http_request(
                    url=url,
                    method=method,
                    headers=self.headers,
                    parameters=parameters,
                    payload=payload,
                    use_proxy=self.helper.get_arg("use_proxy"),
                    verify=VERIFY_REQUESTS,
                    timeout=self.timeout
                )

            # Handle successful response
            if response.status_code in {200, 201}:
                return self._process_response(response, raw_response)
            else:
                return self._log_status_response(response, endpoint)

        except Exception as e:
            # Log critical errors if request fails
            self.log(LogLevel.CRITICAL, "Failed getting data from REST API")
            self.log(LogLevel.CRITICAL, "Exception: {}", str(e))
            raise

    def _process_response(self, response, raw_response):
        """Processes the API response, handling raw or JSON/text based on request."""
        if raw_response:
            return response.raw
        try:
            return response.json()
        except ValueError:
            return response.text

    def _log_status_response(self, response, endpoint):
        """Logs error details for unsuccessful responses."""
        if response.status_code < 400:
            log_level = LogLevel.WARNING
        elif response.status_code < 500:
            log_level = LogLevel.ERROR
        else:
            log_level = LogLevel.CRITICAL

        self.log(log_level, "Received response {} for endpoint {}", response.status_code, endpoint)
        try:
            error_content = response.json()
        except ValueError:
            error_content = response.text
        self.log(LogLevel.ERROR, "Response content: {}", error_content)
        return error_content

    def get_token(self):
        """Get the token for the Guardicore management server."""
        global_account = self.helper.get_arg('guardicore_api_account')
        username = global_account['username']
        password = global_account['password']
        payload = {"username": username, "password": password}

        try:
            return self.request("authenticate", method="POST", payload=payload).get("access_token")
        except Exception as e:
            self.log(LogLevel.ERROR, "Error getting token")
            self.log(LogLevel.ERROR, "Exception: {}", e)

    def get_timestamps(self, endpoint, key, default_days=DEFAULT_BACKTRACK_DAYS):
        """Get the timestamps for the data retrieval. Logic on how to get the timestamps is as follows:
        - If there is no checkpoint and no start_date, the default is to retrieve data from 365 days ago.
        - If there is a start_date but no checkpoint, data is retrieved from the start_date.
        - Otherwise data is retrieved from the checkpoint. Which is the timestamp of the last event retrieved."""

        start_date = self.helper.get_arg("start_date")
        format_key = "{}_{}".format(self.helper.get_arg("name"), key)
        from_time = self.helper.get_check_point(format_key)
        if not start_date and not from_time:
            from_time = self.helper.get_check_point(key) or self.to_timestamp_str(
                datetime.utcnow() - timedelta(days=default_days))
        elif start_date and not from_time:
            from_time = self.to_timestamp_str(
                datetime.strptime(start_date, "%Y/%m/%d"))
        to_time = self.to_timestamp_str(datetime.now() - timedelta(minutes=self.log_export_delay))

        self.log(LogLevel.INFO, "Retrieve {} data from_time: {}, to_time: {}", endpoint, datetime
                 .fromtimestamp(int(from_time) / 1000),
                 datetime.fromtimestamp(
                     int(to_time) / 1000))
        return from_time, to_time

    def get_daily_connections_date(self, date):
        """Get the date for the daily connections."""
        return datetime.strptime(date, "%Y_%m_%d")

    def logout(self):
        """Logout from the Guardicore management server."""
        self.request("logout", method="POST")

    def write_event(self, data):
        """Write an event to the Splunk index."""
        event_data = json.dumps(data)
        ct = datetime.now()
        time = ct.timestamp()

        if "exported_timestamp" in data:
            time = float(data["exported_timestamp"]) / 1000

        event = self.helper.new_event(source=self.helper.get_input_type(), index=self.helper.get_output_index(),
                                      sourcetype=self.helper.get_sourcetype(), time=time, data=event_data)
        self.ew.write_event(event)

    def is_allowed_configured(self, verdicts):
        """Check if the configured policy verdicts includes the 'Allowed' or 'Any' value."""
        return 'Allowed' in verdicts or 'Any' in verdicts

    def get_checkpoint_key(self, key):
        """Get the checkpoint key for the environment."""
        return "{}_{}".format(self.helper.get_arg("name"), key)

    def get_env_checkpoint(self, checkpoint_key):
        """Get the checkpoint for the environment."""
        key = "{}_{}".format(self.helper.get_arg("name"), checkpoint_key)
        return self.helper.get_check_point(key)

    def save_env_checkpoint(self, checkpoint_key, value):
        """Save the checkpoint for the environment."""
        key = "{}_{}".format(self.helper.get_arg("name"), checkpoint_key)

        self.log(LogLevel.DEBUG, "Saving checkpoint for key: {}, value: {}", key, value)
        self.helper.save_check_point(key, value)

    def get_verdict(self, conn):
        """Get the policy verdict of a connection."""
        if conn["policy_verdict"] in ["blocked_by_source", "blocked_by_destination"]:
            return "blocked"
        elif conn["policy_verdict"].startswith("alerted"):
            return "alerted"
        else:
            return "allowed"

    def set_log_exported_timestamp(self, time_value):
        """Set the exported time for an event log"""

        if type(time_value) in [int, float]:
            return time_value

        date_format = self.detect_date_format(time_value)
        if date_format is None:
            self.log(LogLevel.ERROR, "Failed to detect date format for {}", time_value)
            raise ValueError("Failed to detect date format for {}".format(time_value))

        dt = datetime.strptime(time_value, date_format)
        return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)

    def detect_date_format(self, date_string):
        date_formats = [
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d"
        ]

        for date_format in date_formats:
            try:
                datetime.strptime(date_string, date_format)
                return date_format
            except ValueError:
                continue
        return None