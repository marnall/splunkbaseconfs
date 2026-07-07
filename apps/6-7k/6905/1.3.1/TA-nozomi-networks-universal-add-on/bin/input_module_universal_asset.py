# encoding = utf-8

import os
import sys
import time
import datetime
import re
import requests
import logging
import csv
import json
import ast
import urllib3
import random

from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class UniversalApi:
    MAX_RETRIES = 5
    RETRY_MIN_WAIT = 1
    RETRY_MAX_WAIT = 5

    def __init__(self, name, helper):
        self.item_name = name
        global_account = helper.get_arg("global_account")
        self.api_key_name = global_account["username"]
        self.api_key_token = global_account["password"]
        self.from_timestamp = helper.get_arg("from_timestamp")
        self.universal_host = self.__normalize_host(helper.get_arg("universal_host"))

        mode = helper.get_arg("how_assets_are_ingested")

        self.receive_asset_updates = (mode == "receive_asset_updates")
        self.receive_asset_updates_interval = (mode == "receive_asset_updates_interval")
        interval_hours = helper.get_arg("asset_update_interval_hours")
        try:
            # Attempt to convert to float to handle various numeric types
            interval_hours_float = float(interval_hours) if interval_hours is not None else None
            if interval_hours_float is None or interval_hours_float <= 0:
                self.asset_update_interval_hours = 24
            else:
                self.asset_update_interval_hours = interval_hours_float
        except (TypeError, ValueError):
            # If conversion fails, use default
            self.asset_update_interval_hours = 24
        self.helper = helper

        self.helper.log_info(
            f"DEBUG INPUT VALUES -> "
            f"mode={mode!r} (type={type(mode).__name__}), "
            f"receive_asset_updates={self.receive_asset_updates!r} (type={type(self.receive_asset_updates).__name__}), "
            f"receive_asset_updates_interval={self.receive_asset_updates_interval!r} (type={type(self.receive_asset_updates_interval).__name__}), "
            f"asset_update_interval_hours={interval_hours!r} (type={type(interval_hours).__name__})"
        )

        self.PAGE_SIZE = helper.get_arg("page_size")
        self.updated_at_field_exists = None

    def save_current_configuration(self):
        self.helper.save_check_point(self.__input_unique_name() + '_universal_host', self.helper.get_arg('universal_host'))
        self.helper.save_check_point(self.__input_unique_name() + '_from_timestamp',
                                     self.helper.get_arg('from_timestamp'))

    def is_configuration_changed(self):
        return self.helper.get_check_point(self.__input_unique_name() + '_universal_host') != self.helper.get_arg(
            'universal_host') or  self.helper.get_check_point(self.__input_unique_name() + '_from_timestamp') != self.helper.get_arg(
            'from_timestamp')

    def __page(self):
        current_page = self.helper.get_check_point(self.__input_unique_name() + '_page')
        page = 1

        if current_page is not None:
            page = current_page

        self.helper.save_check_point(self.__input_unique_name() + '_page', page)
        return page

    def __increase_page(self):
        current_page = self.helper.get_check_point(self.__input_unique_name() + '_page')
        if current_page is None:
            current_page = 1
        self.helper.save_check_point(self.__input_unique_name() + '_page', current_page + 1)

    @staticmethod
    def __is_ok(response):
        return response.status_code <= 208

    @staticmethod
    def __normalize_host(host):
        if not host:
            raise ValueError("universal_host cannot be empty")
        if host.startswith("https://") or host.startswith("http://"):
            return host
        return "https://" + host

    @staticmethod
    def __get_hostname(host):
        # Remove protocol prefix if present for use in HTTP Host header
        if not host:
            return ""
        if host.startswith("https://"):
            return host[8:]
        elif host.startswith("http://"):
            return host[7:]
        return host

    def __input_unique_name(self):
        return self.item_name + '_' + self.api_key_name

    # This method is to clean page to get again all the elements
    def clean_all(self):
        self.helper.save_check_point(self.__input_unique_name() + '_page', None)
        self.helper.save_check_point(self.__input_unique_name() + '_last_time', None)
        self.helper.save_check_point(self.__input_unique_name() + '_temp_last_time', None)
        self.helper.save_check_point(self.__input_unique_name() + '_last_interval_reset', None)
        self.updated_at_field_exists = None

    def __clean_page(self):
        self.helper.save_check_point(self.__input_unique_name() + '_page', None)

    def __convert_timestamp_to_millis(self, time_value):
        """Convert ISO 8601 timestamp string to milliseconds since epoch.
        Only called when updated_at_field_exists is True for query generation.
        Returns the original value if it's not in ISO 8601 format (e.g., already milliseconds).
        """
        if isinstance(time_value, str):
            # Check if it looks like an ISO 8601 timestamp (contains 'T' and digits with hyphens)
            if 'T' in time_value and '-' in time_value:
                try:
                    # Parse ISO 8601 format like "2025-11-06T09:00:16.348Z" or "2025-11-06T09:00:16Z"
                    # Remove 'Z' suffix (UTC indicator) and parse the timestamp
                    timestamp_str = time_value.rstrip('Z')
                    
                    # Try parsing with fractional seconds first, then without
                    dt = None
                    for fmt in ['%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S']:
                        try:
                            dt = datetime.datetime.strptime(timestamp_str, fmt)
                            break
                        except ValueError:
                            continue
                    
                    if dt is not None:
                        # The datetime object is timezone-naive, representing UTC
                        # Convert to UTC timestamp in milliseconds
                        return int(dt.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
                except (ValueError, AttributeError):
                    pass
            
            # If not ISO 8601 format or parsing failed, return as-is (could be milliseconds string)
            return time_value
        return time_value

    def __save_last_item_time(self, response):
        self.__save_last_item_time_raw(response[-1][self.__resource_time_field()])

    def __save_last_item_time_raw(self, time_value):
        # Save the timestamp as-is without conversion
        self.helper.save_check_point(self.__input_unique_name() + '_last_time', time_value)

    def __save_temp_last_item_time(self, response):
        time_value = response[-1][self.__resource_time_field()]
        # Save the timestamp as-is without conversion
        self.helper.save_check_point(self.__input_unique_name() + '_temp_last_time', time_value)

    def __temp_last_time(self):
        return self.helper.get_check_point(self.__input_unique_name() + '_temp_last_time')

    def __clean_temp_last_item(self):
        self.helper.save_check_point(self.__input_unique_name() + '_temp_last_time', None)

    def __is_update_interval_expired(self):
        """Check if the update interval has expired.
        
        Returns True if:
        - receive_asset_updates_interval is enabled AND
        - Either no last reset timestamp exists OR
        - The time since last reset is >= asset_update_interval_hours
        """
        if not self.receive_asset_updates_interval:
            return False
        
        last_reset = self.helper.get_check_point(self.__input_unique_name() + '_last_interval_reset')
        
        # If no last reset timestamp, interval is considered expired
        if last_reset is None:
            return True
        
        # Calculate time difference
        current_time = int(time.time())
        time_diff_seconds = current_time - last_reset
        time_diff_hours = time_diff_seconds / 3600.0
        
        return time_diff_hours >= self.asset_update_interval_hours

    def __reset_interval_state(self):
        """Reset the pagination and timestamp state for interval-based updates.
        
        This method:
        - Resets _last_time to None (will fall back to from_timestamp)
        - Resets pagination (_page, _temp_last_time)
        - Updates the _last_interval_reset timestamp to current time
        """
        self.helper.log_info(
            f"Asset update interval expired (>{self.asset_update_interval_hours}h), resetting pagination and timestamp"
        )
        
        # Reset last_time to None so it will use from_timestamp
        self.helper.save_check_point(self.__input_unique_name() + '_last_time', None)
        
        # Reset pagination
        self.helper.save_check_point(self.__input_unique_name() + '_page', None)
        self.helper.save_check_point(self.__input_unique_name() + '_temp_last_time', None)
        
        # Update last reset timestamp
        current_time = int(time.time())
        self.helper.save_check_point(self.__input_unique_name() + '_last_interval_reset', current_time)

    def __last_item_time(self):
        saved_last_time = self.helper.get_check_point(self.__input_unique_name() + '_last_time')
        if saved_last_time is None:
            return self.from_timestamp
        else:
            return saved_last_time

    def __retry_request(self, request_func):
        for attempt in range(self.MAX_RETRIES):
            response = request_func()
            
            if response.status_code != 429:
                return response
            
            if attempt < self.MAX_RETRIES - 1:
                wait_time = random.uniform(self.RETRY_MIN_WAIT, self.RETRY_MAX_WAIT)
                self.helper.log_info(
                    f"Received 429 response, retrying in {wait_time:.2f} seconds (attempt {attempt + 1}/{self.MAX_RETRIES})"
                )
                time.sleep(wait_time)
            else:
                self.helper.log_error(
                    f"Received 429 response after {self.MAX_RETRIES} attempts, giving up"
                )
        
        return response

    def __token(self):
        endpoint = self.universal_host + "/api/open/sign_in"
        payload = {'key_name': self.api_key_name, 'key_token': self.api_key_token}

        response = self.__retry_request(lambda: requests.post(endpoint, data=payload, verify=True))

        if self.__is_ok(response) is not True:
            self.helper.log_error(
                "ERROR REST API call /api/open/sign_in returned " + str(response.status_code))
            return None

        bearer_token = response.headers['Authorization']

        return bearer_token

    def __get_headers(self, token):
        return {
            'authorization': token,
            'content-type': 'application/json',
            'host': self.__get_hostname(self.universal_host),
            'nn-app': 'splunk-add-on',
            'nn-app-version': '1.3.1'
        }

    def __check_updated_at_field_exists(self):
        """Check if the updated_at field exists in assets by doing a test query."""
        if self.updated_at_field_exists is not None:
            return self.updated_at_field_exists
        
        token = self.__token()
        if token is None:
            self.helper.log_error("Cannot check updated_at field: authentication failed")
            self.updated_at_field_exists = False
            return False
        
        headers = self.__get_headers(token)
        
        # Test query to check if updated_at field exists
        test_endpoint = self.universal_host + "/api/open/query/do?query=assets | select updated_at&count=1"
        
        try:
            response = self.__retry_request(lambda: requests.get(test_endpoint, headers=headers, verify=True))
            
            if self.__is_ok(response):
                json_response = response.json()
                # If the field doesn't exist, we get an error
                if "error" in json_response and json_response["error"]:
                    self.helper.log_info("updated_at field does not exist in assets, using last_activity_time field as fallback")
                    self.updated_at_field_exists = False
                else:
                    self.helper.log_info("updated_at field exists in assets")
                    self.updated_at_field_exists = True
            else:
                self.helper.log_error(f"Failed to check updated_at field existence: status {response.status_code}")
                self.updated_at_field_exists = False
        except Exception as e:
            self.helper.log_error(f"Exception while checking updated_at field: {str(e)}")
            self.updated_at_field_exists = False

        return self.updated_at_field_exists

    def __full_resource_url(self):
        time_field = self.__resource_time_field()
        page = self.__page()
        # Use to_epoch() when updated_at field is being used (string timestamp needs conversion)
        if self.updated_at_field_exists:
            # Convert the checkpoint value to milliseconds for comparison
            checkpoint_value = self.__convert_timestamp_to_millis(self.__last_item_time())
            time_field_for_query = "to_epoch(" + time_field + ")"
        else:
            checkpoint_value = self.__last_item_time()
            time_field_for_query = time_field
        return self.universal_host + "/api/open/query/do?query=" + self.item_name + " | where " + time_field_for_query + " > " + str(
            checkpoint_value) + " | sort " + time_field + " asc&skip_total_count=true" + "&page=" + str(page) + "&count=" + str(self.PAGE_SIZE) + "&default_filters=false"

    def __resource_time_field(self):
        resource = self.item_name 
        if resource == "alerts":
            return "record_created_at"
        if resource == "assets" and self.receive_asset_updates:
            # Check if updated_at field exists, if not fallback to last_activity_time
            if self.__check_updated_at_field_exists():
                return "updated_at"
            else:
                return "last_activity_time"
        if resource == "assets":
            return "created_at"
        if resource == "sessions":
            return "first_activity_time"
        if resource == "health_log":
            return "record_created_at"
        if resource == "node_cves":
            return "time"
        if resource == "links":
            return "first_activity_time"
        if resource == "variables":
            return "first_activity_time"
        if resource == "nodes":
            return "created_at"
        if resource == "audit_log":
            return "record_created_at"

    def page(self):
        return self.__page()

    def reset_pagination(self):
        if self.__temp_last_time() is not None:
            self.__save_last_item_time_raw(str(self.__temp_last_time()))
        self.__clean_temp_last_item()
        self.__clean_page()

    def next_page_items_with_current_last_item_time(self):
        funct = lambda item: item[self.__resource_time_field()] == self.__temp_last_time()
        return [item for item in self.items_skip_pagination_setup() if funct(item)]

    def items_skip_pagination_setup(self):
        token = self.__token()
        if token is None:
            return []

        headers = self.__get_headers(token)

        endpoint = self.__full_resource_url()
        response = self.__get_items(endpoint, headers)

        if response.status_code >= 500 or response.status_code == 499:
            self.reset_pagination()
            return []

        if self.__is_ok(response) is not True:
            self.helper.log_error(
                "ERROR REST API call /api/open/query/do?query=" + self.item_name + "... returned " + str(
                    response.status_code))
            return []

        json_response = response.json()

        if "error" in json_response and json_response["error"] and json_response["error"] != "":
            self.helper.log_error(
                "ERROR REST API call /api/open/query/do?query=" + self.item_name + "... returned error: " + str(
                    json_response["error"]))

        return json_response["result"]

    def items(self):
        # Check if interval-based updates are enabled and if the interval has expired
        if self.receive_asset_updates_interval:
            if self.__is_update_interval_expired():
                self.__reset_interval_state()
            else:
                # Only log once per interval cycle (when page is 1 or not set)
                current_page = self.helper.get_check_point(self.__input_unique_name() + '_page')
                if current_page is None or current_page == 1:
                    self.helper.log_info(
                        f"Asset update interval not expired yet (<{self.asset_update_interval_hours}h), continuing with normal pagination"
                    )

        result = self.items_skip_pagination_setup()
        response_len = len(result)

        if response_len == int(self.PAGE_SIZE):
            self.__save_temp_last_item_time(result)
            self.__increase_page()
        else:
            self.__clean_page()
            if response_len >= 1:
                self.__save_last_item_time(result)
                self.__clean_temp_last_item()
            else:
                if self.__temp_last_time() is not None:
                    self.__save_last_item_time_raw(str(self.__temp_last_time()))
                    self.__clean_temp_last_item()

        return result

    def __get_items(self, endpoint, headers):
        return self.__retry_request(lambda: requests.get(endpoint, headers=headers, verify=True))


def validate_input(helper, definition):
    # """Implement your own validation logic to validate the input stanza configurations"""
    pass


def collect_events(helper, ew):
    universal_api = UniversalApi('assets', helper)

    if universal_api.is_configuration_changed():
        universal_api.clean_all()
        universal_api.save_current_configuration()

    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)

    result = universal_api.items()

    def extract_id_and_time(item):
        return {'id': item['id'], 'time': item["record_created_at"]}

    def publish(items):
        for item in items:
            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(),
                                     sourcetype=helper.get_sourcetype(), data=json.dumps(item))
            ew.write_event(event)

    # Create a splunk event
    publish(result)

    RESET_AFTER_PAGINATION_COUNT = 100
    if universal_api.page() >= RESET_AFTER_PAGINATION_COUNT:
        next_page_items_with_current_last_item_time = universal_api.next_page_items_with_current_last_item_time()

        publish(next_page_items_with_current_last_item_time)
        universal_api.reset_pagination()
    pass
