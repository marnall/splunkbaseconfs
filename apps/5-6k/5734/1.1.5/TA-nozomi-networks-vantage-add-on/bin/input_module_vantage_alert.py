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

from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class Vantage:

    def __init__(self, name, helper):
        self.item_name = name
        self.api_key_name = helper.get_arg("api_key_name")
        self.api_key_token = helper.get_arg("api_key_token")
        self.from_timestamp = helper.get_arg("from_timestamp")
        self.vantage_host = helper.get_arg("vantage_host")
        self.group_by_incident = helper.get_arg("group_by_incident")
        self.helper = helper
        self.PAGE_SIZE = 1000

    def save_current_configuration(self):
        self.helper.save_check_point(self.__input_unique_name() + '_api_key_name', self.helper.get_arg('api_key_name'))
        self.helper.save_check_point(self.__input_unique_name() + '_api_key_token',
                                     self.helper.get_arg('api_key_token'))
        self.helper.save_check_point(self.__input_unique_name() + '_vantage_host', self.helper.get_arg('vantage_host'))
        self.helper.save_check_point(self.__input_unique_name() + '_organization_name',
                                     self.helper.get_arg('organization_name'))
        self.helper.save_check_point(self.__input_unique_name() + '_from_timestamp',
                                     self.helper.get_arg('from_timestamp'))

    def is_configuration_changed(self):
        return self.helper.get_check_point(self.__input_unique_name() + '_api_key_name') != self.helper.get_arg(
            'api_key_name') or self.helper.get_check_point(self.__input_unique_name() + '_api_key_token') != self.helper.get_arg(
            'api_key_token') or self.helper.get_check_point(self.__input_unique_name() + '_vantage_host') != self.helper.get_arg(
            'vantage_host') or self.helper.get_check_point(self.__input_unique_name() + '_organization_name') != self.helper.get_arg(
            'organization_name') or self.helper.get_check_point(self.__input_unique_name() + '_from_timestamp') != self.helper.get_arg(
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

    def __input_unique_name(self):
        return self.item_name + '_' + self.api_key_name

    # This method is to clean page to get again all the elements
    def clean_all(self):
        self.helper.save_check_point(self.__input_unique_name() + '_page', None)
        self.helper.save_check_point(self.__input_unique_name() + '_last_time', None)
        self.helper.save_check_point(self.__input_unique_name() + '_before_last_time', None)
        self.helper.save_check_point(self.__input_unique_name() + '_token', None)

    def __clean_page(self):
        self.helper.save_check_point(self.__input_unique_name() + '_page', None)

    def __clean_last_token(self):
        self.helper.save_check_point(self.__input_unique_name() + '_token', None)

    def __save_last_item_time(self, response):
        self.__save_before_last_item_time(response)
        self.__save_last_item_time_raw(response[-1]['attributes']['record_created_at'])

    def __save_last_item_time_raw(self, time_value):
        self.helper.save_check_point(self.__input_unique_name() + '_last_time', time_value)

    def __save_before_last_item_time(self, response):
        self.helper.save_check_point(self.__input_unique_name() + '_before_last_time', response[-1]['attributes']['record_created_at'])

    def __before_last_time(self):
        return self.helper.get_check_point(self.__input_unique_name() + '_before_last_time')

    def save_last_received_token(self, token):
        self.helper.save_check_point(self.__input_unique_name() + '_token', token)

    def __last_received_token(self):
        return self.helper.get_check_point(self.__input_unique_name() + '_token')

    def __last_item_time(self):
        saved_last_time = self.helper.get_check_point(self.__input_unique_name() + '_last_time')
        if saved_last_time is None:
            return self.from_timestamp
        else:
            return saved_last_time

    def __token(self):
        last_token = self.__last_received_token()
        if last_token is not None:
            return last_token
        else:
            endpoint = "https://" + self.vantage_host + "/api/v1/keys/sign_in"
            payload = {'key_name': self.api_key_name, 'key_token': self.api_key_token}

            response = requests.post(endpoint, data=payload)

            if self.__is_ok(response) is not True:
                self.helper.log_error(
                    "ERROR REST API call /api/v1/keys/sign_in returned " + str(response.status_code))
                return None

            bearer_token = response.headers['Authorization']

#             self.helper.log_info("NEW token " + bearer_token)
            self.save_last_received_token(bearer_token)

            return bearer_token

    def __organization_id_from(self, organization_name):

        endpoint = "https://" + self.vantage_host + "/api/v1/admin/organizations?filter[name]=" + organization_name
        # self.helper.log_info('__organization_id_from endpoint ' + endpoint)
        token = self.__token()
        headers = {
            'authorization': token,
            'content-type': 'application/json'
        }

        response = requests.get(endpoint, headers=headers)

        if self.__is_ok(response) is not True:
            self.helper.log_error(
                "ERROR REST API call /api/v1/admin/organizations returned " + str(response.status_code))
            return ''

        json_response = response.json()
        if len(json_response['data']) > 0:
            return json_response['data'][0]['id']
        else:
            return ''

    def page(self):
        return self.__page()

    def reset_pagination(self):
        return self.__clean_page()

    def items(self):
        token = self.__token()
        organization_id = self.__organization_id_from(self.helper.get_arg('organization_name'))

        headers = {
            'authorization': token,
            'Vantage-Org': organization_id,
            'content-type': 'application/json'
        }

        page = self.__page()

        endpoint = "https://" + self.vantage_host + "/api/v1/" + self.item_name + "?sort[record_created_at]=asc&skip_total_count=true&filter[record_created_at][gt]=" + str(
            self.__last_item_time()) + "&page=" + str(page) + "&size=" + str(self.PAGE_SIZE) + "&default_filters=" + str(self.group_by_incident).lower()

        self.helper.log_info('XXX endpoint item' + endpoint)

        response = requests.get(endpoint, headers=headers)

        if response.status_code == 401:
            self.__clean_last_token()
            return {'data': []}

        if self.__is_ok(response) is not True:
            self.helper.log_error(
                "ERROR REST API call /api/v1/" + self.item_name + " returned " + str(response.status_code))
            return {'data': []}

        json_response = response.json()

        response_len = len(json_response["data"])
        
        self.helper.log_info('XXX response_len ' + str(response_len))

        if response_len == self.PAGE_SIZE:
            self.__save_before_last_item_time(json_response["data"])

            RESET_AFTER_PAGINATION_COUNT = 100
            if page == RESET_AFTER_PAGINATION_COUNT:
                self.__clean_page()
                self.__save_last_item_time(json_response["data"])
            else:
                self.__increase_page()
        else:
            self.__clean_page()
            if response_len >= 1:
                self.__save_last_item_time(json_response["data"])
            else:
                if self.__before_last_time() is not None:
                    self.__save_last_item_time_raw(str(self.__before_last_time()))
        return json_response


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    pass


def flat_and_filter_json_response_data(response_data):
    flattened_data = []
    for item in response_data:
        flattened_item = {}
        for key in item.keys():
            if key != "attributes" and key != "relationships" and key != "links":
                flattened_item[key] = item[key]
        if "attributes" in item.keys():
            item_attributes = item["attributes"]
            for key in item_attributes.keys():
                flattened_item[key] = item_attributes[key]
        flattened_data.append(flattened_item)
    return flattened_data


def collect_events(helper, ew):
   # helper.log_info("-----------------A NEW RUN START HERE------------------")

    vantage = Vantage('alerts', helper)

    if vantage.is_configuration_changed():
        #vantage.helper.log_info('clean token, page and last time')
        vantage.clean_all()
        vantage.save_current_configuration()

    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)

    json_response = vantage.items()
    response_data = json_response["data"]
    flattened_data = flat_and_filter_json_response_data(response_data)

    # Create a splunk event
    for item in flattened_data:
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(item))
        ew.write_event(event)
    pass
