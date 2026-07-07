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
        self.helper = helper
        self.PAGE_SIZE = helper.get_arg("page_size")

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

    def __clean_page(self):
        self.helper.save_check_point(self.__input_unique_name() + '_page', None)

    def __save_last_item_time(self, response):
        self.__save_last_item_time_raw(response[-1][self.__resource_time_field()])

    def __save_last_item_time_raw(self, time_value):
        self.helper.save_check_point(self.__input_unique_name() + '_last_time', time_value)

    def __save_temp_last_item_time(self, response):
        self.helper.save_check_point(self.__input_unique_name() + '_temp_last_time', response[-1][self.__resource_time_field()])

    def __temp_last_time(self):
        return self.helper.get_check_point(self.__input_unique_name() + '_temp_last_time')

    def __clean_temp_last_item(self):
        self.helper.save_check_point(self.__input_unique_name() + '_temp_last_time', None)

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

    def __full_resource_url(self):
        time_field = self.__resource_time_field()
        page = self.__page()
        return self.universal_host + "/api/open/query/do?query=" + self.item_name + " | where " + time_field + " > " + str(
            self.__last_item_time()) + " | sort " + time_field + " asc&skip_total_count=true" + "&page=" + str(page) + "&count=" + str(self.PAGE_SIZE) + "&default_filters=false"

    def __resource_time_field(self):
        resource = self.item_name
        if resource == "alerts":
            return "record_created_at"
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

        headers = {
            'authorization': token,
            'content-type': 'application/json',
            'host': self.__get_hostname(self.universal_host),
            'nn-app': 'splunk-add-on',
            'nn-app-version': '1.2.1'
        }

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
    universal_api = UniversalApi('links', helper)

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
