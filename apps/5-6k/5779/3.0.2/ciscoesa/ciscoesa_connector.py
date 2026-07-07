# File: ciscoesa_connector.py
#
# Copyright (c) 2017-2025 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#
#
import base64
import datetime
import json
import re
import socket
import urllib

import phantom.app as phantom
import requests
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

import ciscoesa_consts as consts
import ciscoesa_helper


# Dictionary that maps each error code with its corresponding message
ERROR_RESPONSE_DICT = {
    consts.CISCOESA_REST_RESP_BAD_REQUEST: consts.CISCOESA_REST_RESP_BAD_REQUEST_MESSAGE,
    consts.CISCOESA_REST_RESP_UNAUTHORIZED: consts.CISCOESA_REST_RESP_UNAUTHORIZED_MESSAGE,
    consts.CISCOESA_REST_RESP_FORBIDDEN: consts.CISCISCOESA_REST_RESP_FORBIDDEN_MESSAGE,
    consts.CISCOESA_REST_RESP_NOT_FOUND: consts.CISCOESA_REST_RESP_NOT_FOUND_MESSAGE,
    consts.CISCOESA_REST_RESP_INTERNAL_SERVER_ERROR: consts.CISCOESA_REST_RESP_INTERNAL_SERVER_ERROR_MESSAGE,
    consts.CISCOESA_REST_RESP_NOT_ACCEPTABLE: consts.CISCOESA_REST_RESP_NOT_ACCEPTABLE_MESSAGE,
    consts.CISCOESA_REST_RESP_ENTITY_TOO_LARGE: consts.CISCOESA_REST_RESP_ENTITY_TOO_LARGE_MESSAGE,
    consts.CISCOESA_REST_RESP_URI_TOO_LONG: consts.CISCOESA_REST_RESP_URI_TOO_LONG_MESSAGE,
    consts.CISCOESA_REST_RESP_NOT_IMPLEMENTED: consts.CISCOESA_REST_RESP_NOT_IMPLEMENTED_MESSAGE,
    consts.CISCOESA_REST_RESP_BAD_GATEWAY: consts.CISCOESA_REST_RESP_BAD_GATEWAY_MESSAGE,
}

# Object that maps report title with its corresponding endpoint
# key: report title
# value: report endpoint
REPORT_TITLE_TO_NAME_AND_FILTER_MAPPING = {
    consts.CISCOESA_MAIL_USER_DETAILS_REPORT_TITLE: consts.CISCOESA_MAIL_USER_DETAILS_REPORT_NAME,
    consts.CISCOESA_MAIL_INCOMING_DOMAIN_DETAILS_REPORT_TITLE: consts.CISCOESA_MAIL_INCOMING_DOMAIN_DETAILS_REPORT_NAME,
    consts.CISCOESA_MAIL_INCOMING_IP_HOSTNAME_DETAILS_REPORT_TITLE: consts.CISCOESA_MAIL_INCOMING_IP_HOSTNAME_DETAILS_REPORT_NAME,
    consts.CISCOESA_MAIL_INCOMING_NETWORK_OWNER_DETAILS_REPORT_TITLE: consts.CISCOESA_MAIL_INCOMING_NETWORK_OWNER_DETAILS_REPORT_NAME,
    consts.CISCOESA_OUTGOING_SENDERS_DOMAIN_DETAILS_REPORT_TITLE: consts.CISCOESA_OUTGOING_SENDERS_DOMAIN_DETAILS_REPORT_NAME,
    consts.CISCOESA_MAIL_OUTGOING_SENDERS_IP_HOSTNAME_DETAILS_REPORT_TITLE: consts.CISCOESA_MAIL_OUTGOING_SENDERS_IP_HOSTNAME_DETAILS_REPORT_NAME,
    consts.CISCOESA_OUTGOING_CONTENT_FILTERS_REPORT_TITLE: consts.CISCOESA_OUTGOING_CONTENT_FILTERS_REPORT_NAME,
    consts.CISCOESA_OUTGOING_DESTINATIONS_REPORT_TITLE: consts.CISCOESA_OUTGOING_DESTINATIONS_REPORT_NAME,
    consts.CISCOESA_VIRUS_TYPES_REPORT_TITLE: consts.CISCOESA_VIRUS_TYPES_REPORT_NAME,
    consts.CISCOESA_INBOUND_SMTP_AUTH_REPORT_TITLE: consts.CISCOESA_INBOUND_SMTP_AUTH_REPORT_NAME,
    consts.CISCOESA_DLP_OUTGOING_POLICY_REPORT_TITLE: consts.CISCOESA_DLP_OUTGOING_POLICY_REPORT_NAME,
}


def _is_ip(ip_address):
    """Function that validates IP address (IPv4 or IPv6).

    :param ip_address: IP address to verify
    :return: True or False
    """

    # Validate IP address
    if not phantom.is_ip(ip_address):
        try:
            socket.inet_pton(socket.AF_INET6, ip_address)
        except OSError:
            return False

    return True


class CiscoesaConnector(BaseConnector):
    """This is an AppConnector class that inherits the BaseConnector class. It implements various actions supported by
    Cisco ESA and helper methods required to run the actions.
    """

    def __init__(self):
        # Calling the BaseConnector's init function
        super().__init__()

        self._url = None
        self._username = None
        self._password = None
        self._verify_server_cert = False

        return

    def _get_error_message_from_exception(self, e):
        """This function is used to get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """
        error_message = consts.CISCOESA_ERROR_MESSAGE
        error_code = consts.CISCOESA_ERROR_CODE_MESSAGE
        self.error_print("Exception occurred: ", e)

        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_code = consts.CISCOESA_ERROR_CODE_MESSAGE
                    error_message = e.args[0]
        except Exception as ex:
            self.error_print("Error occurred while retrieving exception information: ", ex)

        if not error_code:
            error_text = f"Error Message: {error_message}"
        else:
            error_text = consts.CISCOESA_ERROR_MESSAGE_FORMAT.format(error_code, error_message)

        return error_text

    def initialize(self):
        """This is an optional function that can be implemented by the AppConnector derived class. Since the
        configuration dictionary is already validated by the time this function is called, it's a good place to do any
        extra initialization of any internal modules. This function MUST return a value of either phantom.APP_SUCCESS or
        phantom.APP_ERROR. If this function returns phantom.APP_ERROR, then AppConnector::handle_action will not get
        called.
        """

        config = self.get_config()
        self._url = config[consts.CISCOESA_CONFIG_URL].strip("/")
        self._username = config[consts.CISCOESA_CONFIG_USERNAME]
        self._password = config[consts.CISCOESA_CONFIG_PASSWORD]
        self._verify_server_cert = config.get(consts.CISCOESA_CONFIG_VERIFY_SSL, False)
        self._esa_helper = ciscoesa_helper.CiscoEsaHelper(
            self, config.get(consts.CISCOESA_CONFIG_SSH_USERNAME), config.get(consts.CISCOESA_CONFIG_SSH_PASSWORD), self._url
        )

        # In "get report" action, if "starts_with" parameter is set, validate IP and email
        self.set_validator(consts.CISCOESA_CONTAINS_IP, None)
        self.set_validator(consts.CISCOESA_CONTAINS_EMAIL, None)

        return phantom.APP_SUCCESS

    def _validate_integers(self, action_result, parameter, key, allow_zero=False):
        """This method is to check if the provided input parameter value
        is a non-zero positive integer and returns the integer value of the parameter itself.
        :param action_result: Action result or BaseConnector object
        :param parameter: input parameter
        :return: integer value of the parameter or None in case of failure
        """

        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    action_result.set_status(phantom.APP_ERROR, consts.CISCOESA_VALIDATE_INTEGER_MESSAGE.format(key=key))
                    return None
                parameter = int(parameter)

            except Exception:
                action_result.set_status(phantom.APP_ERROR, consts.CISCOESA_VALIDATE_INTEGER_MESSAGE.format(key=key))
                return None

            if parameter < 0:
                action_result.set_status(phantom.APP_ERROR, f"Please provide a valid non-negative integer value in the {key} parameter")
                return None
            if not allow_zero and parameter == 0:
                action_result.set_status(phantom.APP_ERROR, f"Please provide non-zero positive integer in {key}")
                return None

        return parameter

    def _validate_date_time(self, date_time_value, action_result):
        """Function used to validate date and time format. As per the app configuration, date and time must be provided
        in YYYY-MM-DDTHH:00 format.

        :param date_time_value: date and time value that needs to be split and validated
        :param action_result: Object of ActionResult class
        :return: status success/failure and (parsed datetime or None)
        """

        date_time = date_time_value.split("T")

        # If given datetime not in expected format
        if len(date_time) <= 1:
            self.error_print(consts.CISCOESA_DATE_TIME_FORMAT_ERROR)
            return action_result.set_status(phantom.APP_ERROR, consts.CISCOESA_DATE_TIME_FORMAT_ERROR), None

        if len(date_time[1].split(":")) != 2:
            self.error_print(consts.CISCOESA_DATE_TIME_FORMAT_ERROR)
            return action_result.set_status(phantom.APP_ERROR, consts.CISCOESA_DATE_TIME_FORMAT_ERROR), None

        date = date_time[0].split("-")
        hour = date_time[1].split(":")[0]

        if len(date) != 3:
            self.error_print(consts.CISCOESA_DATE_TIME_FORMAT_ERROR)
            return action_result.set_status(phantom.APP_ERROR, consts.CISCOESA_DATE_TIME_FORMAT_ERROR), None

        try:
            parsed_date_time = datetime.datetime(year=int(date[0]), month=int(date[1]), day=int(date[2]), hour=int(hour))
        except Exception:
            self.error_print(consts.CISCOESA_DATE_TIME_VALIDATION_ERROR)
            return action_result.set_status(phantom.APP_ERROR, consts.CISCOESA_DATE_TIME_VALIDATION_ERROR), None

        return phantom.APP_SUCCESS, parsed_date_time

    def _make_rest_call(self, endpoint, action_result, params=None, method="get", timeout=None):
        """Function that makes the REST call to the device. It is a generic function that can be called from various
        action handlers.

        :param endpoint: REST endpoint that needs to be appended to the service address
        :param action_result: object of ActionResult class
        :param params: request parameters if method is get
        :param method: get/post/put/delete ( Default method will be "get" )
        :param timeout: request timeout in seconds
        :return: status success/failure(along with appropriate message), response obtained by making an API call
        """

        response_data = None

        try:
            request_func = getattr(requests, method)

        except AttributeError:
            self.error_print(consts.CISCOESA_ERROR_API_UNSUPPORTED_METHOD.format(method=method))
            return action_result.set_status(phantom.APP_ERROR, consts.CISCOESA_ERROR_API_UNSUPPORTED_METHOD), response_data

        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, consts.CISCOESA_EXCEPTION_OCCURRED, e), response_data

        auth_string = f"{self._username}:{self._password}"

        credentials = base64.b64encode(auth_string.encode("utf-8")).decode()

        headers = {"Accept": "application/json", "Authorization": f"Basic {credentials}"}

        try:
            response = request_func(
                f"{self._url}{endpoint}",
                params=params,
                headers=headers,
                timeout=consts.CISCOESA_REQUEST_TIMEOUT,
                verify=self._verify_server_cert,
            )
        except Exception as e:
            self.error_print(consts.CISCOESA_ERROR_SERVER_CONNECTIVITY, e)
            return action_result.set_status(phantom.APP_ERROR, consts.CISCOESA_ERROR_SERVER_CONNECTIVITY, e), response_data

        # Try parsing the json
        try:
            content_type = response.headers.get("content-type")
            if content_type and content_type.find("json") != -1:
                response_data = response.json()
            else:
                response_data = response.text

        except Exception as e:
            # r.text is guaranteed to be NON None, it will be empty, but not None
            msg_string = consts.CISCOESA_ERROR_JSON_PARSE.format(raw_text=response.text)
            self.error_print(msg_string, e)
            return action_result.set_status(phantom.APP_ERROR, msg_string, e), response_data

        if response.status_code in ERROR_RESPONSE_DICT:
            message = ERROR_RESPONSE_DICT[response.status_code]

            # overriding message if available in response
            if isinstance(response_data, dict):
                message = response_data.get("error", {}).get("message", message)

            self.error_print(consts.CISCOESA_ERROR_FROM_SERVER.format(status=response.status_code, detail=message))
            return action_result.set_status(
                phantom.APP_ERROR, consts.CISCOESA_ERROR_FROM_SERVER, status=response.status_code, detail=message
            ), response_data

        # In case of success scenario
        if response.status_code == consts.CISCOESA_REST_RESP_SUCCESS:
            # If response obtained is not in object format
            if not isinstance(response_data, dict):
                self.error_print(consts.CISCOESA_UNEXPECTED_RESPONSE.format(report_name=response_data))
                return action_result.set_status(
                    phantom.APP_ERROR, consts.CISCOESA_UNEXPECTED_RESPONSE.format(report_name=response_data)
                ), response_data

            return phantom.APP_SUCCESS, response_data

        # If response code is unknown
        message = consts.CISCOESA_REST_RESP_OTHER_ERROR_MESSAGE

        if isinstance(response_data, dict):
            message = response_data.get("error", {}).get("message", message)

        self.error_print(consts.CISCOESA_ERROR_FROM_SERVER.format(status=response.status_code, detail=message))

        return action_result.set_status(
            phantom.APP_ERROR, consts.CISCOESA_ERROR_FROM_SERVER, status=response.status_code, detail=message
        ), response_data

    def _decode_url(self, param):
        """Process URL and return it stripped
        of the 'secure-web.cisco.com' portion and unquoted

        :param param: dictionary of input parameters
        :return: status success/failure
        """

        self.save_progress("Decoding URL")

        action_result = self.add_action_result(ActionResult(dict(param)))

        encoded_url = param["encoded_url"]
        sw_match = re.match(r"^(https?://)?secure-web\.cisco\.com/.+/(?P<quoted>.+)$", encoded_url)

        # Parse the URL if it looks like what we are expecting otherwise return the whole URL unquoted.
        if sw_match:
            message = "Parsed from secure-web.cisco.com URL and decoded"
            if sw_match.group("quoted"):
                decode_me = sw_match.group("quoted")
            else:
                decode_me = encoded_url.split("/")[-1]
        else:
            message = "Decoded entire URL"
            decode_me = encoded_url

        action_result.add_data({"decoded_url": urllib.parse.unquote(decode_me)})

        self.save_progress("Decoding URL succeeded")

        return action_result.set_status(phantom.APP_SUCCESS, message)

    def _get_report(self, param):
        """Function to retrieve statistical report from the Email Security appliance.

        :param param: dictionary of input parameters
        :return: status success/failure
        """

        action_result = self.add_action_result(ActionResult(dict(param)))
        api_params = {"device_type": "esa"}

        # Getting mandatory parameters
        report_title = param[consts.CISCOESA_GET_REPORT_JSON_REPORT_TITLE]
        if report_title not in consts.CISCOESA_REPORT_TITLE:
            return action_result.set_status(phantom.APP_ERROR, consts.CISCOESA_REPORT_TITLE_ERROR)

        # Getting optional parameters
        start_time = param.get(consts.CISCOESA_GET_REPORT_JSON_START_TIME)
        end_time = param.get(consts.CISCOESA_GET_REPORT_JSON_END_TIME)
        filter_by = param.get(consts.CISCOESA_GET_REPORT_JSON_FILTER_BY)
        filter_value = param.get(consts.CISCOESA_GET_REPORT_JSON_FILTER_VALUE)
        limit = self._validate_integers(
            action_result, param.get(consts.CISCOESA_GET_REPORT_JSON_LIMIT, consts.CISCOESA_DEFAULT_LIMIT), consts.CISCOESA_GET_REPORT_JSON_LIMIT
        )
        if limit is None:
            return action_result.get_status()
        offset = self._validate_integers(
            action_result,
            param.get(consts.CISCOESA_GET_REPORT_JSON_OFFSET, consts.CISCOESA_DEFAULT_OFFSET),
            consts.CISCOESA_GET_REPORT_JSON_OFFSET,
            allow_zero=True,
        )
        if offset is None:
            return action_result.get_status()
        starts_with = param.get(consts.CISCOESA_GET_REPORT_JSON_STARTS_WITH)
        order_by = param.get(consts.CISCOESA_GET_REPORT_JSON_ORDER_BY)
        order_dir = param.get(consts.CISCOESA_GET_REPORT_JSON_ORDER_DIR)

        api_params[consts.CISCOESA_GET_REPORT_JSON_LIMIT] = limit
        api_params[consts.CISCOESA_GET_REPORT_JSON_OFFSET] = offset

        # If both start_time and end_time is not given, then by default, API will query report for last 250 days
        if not start_time and not end_time:
            start_time = (datetime.datetime.now() - datetime.timedelta(days=consts.CISCOESA_DEFAULT_SPAN_DAYS)).strftime(
                consts.CISCOESA_INPUT_TIME_FORMAT
            )

            end_time = datetime.datetime.now().strftime(consts.CISCOESA_INPUT_TIME_FORMAT)

        # If start_time is given, but end_time is not given
        elif not end_time:
            try:
                # end_time will be calculated equivalent to given start_time
                end_time = datetime.datetime.strptime(start_time, consts.CISCOESA_INPUT_TIME_FORMAT) + datetime.timedelta(
                    days=consts.CISCOESA_DEFAULT_SPAN_DAYS
                )
                # If calculated end_time is a future date, then it will be replaced by current date
                if (
                    datetime.datetime.strptime(start_time, consts.CISCOESA_INPUT_TIME_FORMAT)
                    + datetime.timedelta(days=consts.CISCOESA_DEFAULT_SPAN_DAYS)
                    >= datetime.datetime.now()
                ):
                    end_time = datetime.datetime.now()
            except Exception:
                self.error_print(consts.CISCOESA_DATE_TIME_FORMAT_ERROR)
                return action_result.set_status(phantom.APP_ERROR, consts.CISCOESA_DATE_TIME_FORMAT_ERROR)

            # Converting date in string format
            end_time = end_time.strftime(consts.CISCOESA_INPUT_TIME_FORMAT)

        # If start_time is not given, but end_time is given
        elif not start_time:
            try:
                # start_time will be calculated equivalent to given end_time
                temp_time1 = datetime.datetime.strptime(end_time, consts.CISCOESA_INPUT_TIME_FORMAT)
                temp_time2 = datetime.timedelta(days=consts.CISCOESA_DEFAULT_SPAN_DAYS)
                start_time = (temp_time1 - temp_time2).strftime(consts.CISCOESA_INPUT_TIME_FORMAT)
            except Exception:
                self.error_print(consts.CISCOESA_DATE_TIME_FORMAT_ERROR)
                return action_result.set_status(phantom.APP_ERROR, consts.CISCOESA_DATE_TIME_FORMAT_ERROR)

        # Validating start_time
        validate_status, parsed_start_time = self._validate_date_time(start_time, action_result)
        if phantom.is_fail(validate_status):
            return action_result.get_status()

        # Validating end_time
        validate_status, parsed_end_time = self._validate_date_time(end_time, action_result)
        if phantom.is_fail(validate_status):
            return action_result.get_status()

        # Comparing start time and end time
        if parsed_start_time >= parsed_end_time:
            self.error_print(consts.CISCOESA_START_TIME_GREATER_THEN_END_TIME)
            return action_result.set_status(phantom.APP_ERROR, consts.CISCOESA_START_TIME_GREATER_THEN_END_TIME)

        # if starts_with parameter is not set, then IP and email must be validated
        # Search value should be validated to be either an IP address or an email, if report title is
        # "Incoming Mail: IP Addresses", "Outgoing Senders: IP Addresses" or "Internal Users"
        if not starts_with and (filter_by and filter_value):
            if (
                report_title
                in [
                    consts.CISCOESA_MAIL_INCOMING_IP_HOSTNAME_DETAILS_REPORT_TITLE,
                    consts.CISCOESA_MAIL_OUTGOING_SENDERS_IP_HOSTNAME_DETAILS_REPORT_TITLE,
                ]
                and not _is_ip(filter_value)
            ) or (report_title == consts.CISCOESA_MAIL_USER_DETAILS_REPORT_TITLE and not phantom.is_email(filter_value)):
                self.error_print(consts.CISCOESA_SEARCH_VALUE_VALIDATION_FAIL)
                return action_result.set_status(phantom.APP_ERROR, consts.CISCOESA_SEARCH_VALUE_VALIDATION_FAIL)

        # Report will be queried for last given duration period
        # Time zone that will be considered for calculating time and date will be GMT having 00:00 offset from UTC
        # Time to query the report supports only 00 minutes
        try:
            start_time = parsed_start_time.strftime(consts.CISCOESA_API_TIME_FORMAT)
            end_time = parsed_end_time.strftime(consts.CISCOESA_API_TIME_FORMAT)
        except Exception as error:
            return action_result.set_status(phantom.APP_ERROR, self._get_error_message_from_exception(error))

        api_params[consts.CISCOESA_GET_REPORT_PARAM_START_DATE] = start_time
        api_params[consts.CISCOESA_GET_REPORT_PARAM_END_DATE] = end_time

        # Obtain report name
        report_name = REPORT_TITLE_TO_NAME_AND_FILTER_MAPPING[report_title]

        if filter_by:
            api_params[consts.CISCOESA_GET_REPORT_JSON_FILTER_BY_KEY] = filter_by
        if filter_value:
            api_params[consts.CISCOESA_GET_REPORT_JSON_FILTER_VALUE_KEY] = filter_value

        if filter_by and filter_value:
            if starts_with:
                api_params[consts.CISCOESA_GET_REPORT_JSON_FILTER_OPERATOR] = "begins_with"
            else:
                api_params[consts.CISCOESA_GET_REPORT_JSON_FILTER_OPERATOR] = "is"

        if order_by:
            api_params[consts.CISCOESA_GET_REPORT_JSON_ORDER_BY_KEY] = order_by
        if order_dir:
            if order_dir not in consts.CISCOESA_ORDER_DIR:
                return action_result.set_status(phantom.APP_ERROR, consts.CISCOESA_ORDER_DIR_ERROR)
            api_params[consts.CISCOESA_GET_REPORT_JSON_ORDER_DIR_KEY] = order_dir

        report_endpoint = consts.CISCOESA_GET_REPORT_ENDPOINT.format(report_name=report_name)
        self.send_progress(consts.CISCOESA_GET_REPORT_INTERMEDIATE_MESSAGE.format(report_title=report_title))

        # Making REST call to get report data
        response_status, report_data = self._make_rest_call(report_endpoint, action_result, params=api_params)

        # Something went wrong while querying a report
        if phantom.is_fail(response_status):
            self.error_print(consts.CISCOESA_GET_REPORT_ERROR.format(report_title=report_title))
            return action_result.get_status()
        action_result.add_data(report_data)

        return action_result.set_status(phantom.APP_SUCCESS, consts.CISCOESA_REPORTS_QUERIED_SUCCESS_MESSAGE)

    def _test_asset_connectivity(self, param):
        """This function tests the connectivity of an asset with given credentials.

        :param param: (not used in this method)
        :return: status success/failure
        """

        action_result = ActionResult()

        self.save_progress(consts.CISCOESA_CONNECTIVITY_TEST_MESSAGE)
        self.save_progress(f"Configured URL: {self._url}")

        ret_value, response = self._make_rest_call(
            endpoint=consts.CISCOESA_TEST_CONNECTIVITY_ENDPOINT, action_result=action_result, timeout=consts.CISCOESA_REQUEST_TIMEOUT
        )

        if phantom.is_fail(ret_value):
            self.save_progress(action_result.get_message())
            self.set_status(phantom.APP_ERROR, consts.CISCOESA_TEST_CONNECTIVITY_FAIL)
            return action_result.get_status()

        self.set_status_save_progress(phantom.APP_SUCCESS, consts.CISCOESA_TEST_CONNECTIVITY_SUCCESS)

        return action_result.get_status()

    def _handle_list_dictionary_items(self, param):
        """Function to list all entries of an ESA dictionary.
        :param param: dictionary of input parameters
        :return: status success/failure
        """
        action_result = self.add_action_result(ActionResult(dict(param)))
        dictionary_name = param[consts.CISCOESA_JSON_NAME]
        cluster_mode = param.get(consts.CISCOESA_JSON_CLUSTER_MODE, False)

        self.save_progress(f"Using ESA Helper to list dictionary entries for: {dictionary_name}")
        # use helper to execute commands on ESA
        success, output, exit_status = self._esa_helper.list_dictionary_items(dictionary_name, cluster_mode)
        if not success:
            return action_result.set_status(
                phantom.APP_ERROR, consts.CISCOESA_LIST_DICTIONARY_ERROR_MESSAGE.format(dictionary_name=dictionary_name, error=output)
            )
        self.save_progress(f"Fetched dictionary entries for: {dictionary_name}")
        dictionary_items = output.splitlines()
        item_count = 0
        for item in dictionary_items:
            if len(item.strip()):
                details = item.split(",")
                # expecting at least two values in each item
                if len(details) < 2:
                    continue
                details_dict = {"value": ",".join(str(val) for val in details[:-1])}
                if len(details) > 1:
                    details_dict["weight"] = details[-1].strip()

                action_result.add_data(details_dict)
                item_count = item_count + 1
        summary = {"total_items": item_count}
        action_result.set_summary(summary)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_add_dictionary_item(self, param):
        """Function to add an entry to an ESA dictionary.
        :param param: dictionary of input parameters
        :return: status success/failure
        """
        action_result = self.add_action_result(ActionResult(dict(param)))
        dictionary_name = param[consts.CISCOESA_JSON_NAME]
        entry_value = param[consts.CISCOESA_JSON_VALUE]
        commit_message = param[consts.CISCOESA_JSON_COMMIT_MESSAGE]
        cluster_mode = param.get(consts.CISCOESA_JSON_CLUSTER_MODE, False)

        self.save_progress(f"Using ESA Helper to add dictionary entries for: {dictionary_name}")
        # use helper to execute commands on ESA
        success, output, exit_status = self._esa_helper.add_dictionary_item(dictionary_name, entry_value, commit_message, cluster_mode)
        if not success or (output and consts.CISCOESA_MODIFY_DICTIONARY_INVALID_ESCAPE_CHAR in output):
            return action_result.set_status(
                phantom.APP_ERROR, consts.CISCOESA_ADD_DICTIONARY_ERROR_MESSAGE.format(dictionary_name=dictionary_name, error=output)
            )
        self.save_progress(f"Added entry to dictionary: {dictionary_name}")
        if output:
            action_result.add_data({"message": output})
            return action_result.set_status(phantom.APP_ERROR, output)
        else:
            return action_result.set_status(phantom.APP_SUCCESS, consts.CISCOESA_ADD_DICTIONARY_SUCCESS_MESSAGE)

    def _handle_remove_dictionary_item(self, param):
        """Function to remove an entry from an ESA dictionary.
        :param param: dictionary of input parameters
        :return: status success/failure
        """
        action_result = self.add_action_result(ActionResult(dict(param)))
        dictionary_name = param[consts.CISCOESA_JSON_NAME]
        entry_value = param[consts.CISCOESA_JSON_VALUE]
        commit_message = param[consts.CISCOESA_JSON_COMMIT_MESSAGE]
        cluster_mode = param.get(consts.CISCOESA_JSON_CLUSTER_MODE, False)

        self.save_progress(f"Using ESA Helper to remove dictionary entries for: {dictionary_name}")
        # use helper to execute commands on ESA
        success, output, exit_status = self._esa_helper.remove_dictionary_item(dictionary_name, entry_value, commit_message, cluster_mode)
        if not success or (output and consts.CISCOESA_MODIFY_DICTIONARY_INVALID_ESCAPE_CHAR in output):
            return action_result.set_status(
                phantom.APP_ERROR, consts.CISCOESA_REMOVE_DICTIONARY_ERROR_MESSAGE.format(dictionary_name=dictionary_name, error=output)
            )
        self.save_progress(f"Removed entry from dictionary: {dictionary_name}")
        if output:
            action_result.add_data({"message": output})
            return action_result.set_status(phantom.APP_ERROR, output)
        else:
            return action_result.set_status(phantom.APP_SUCCESS, consts.CISCOESA_REMOVE_DICTIONARY_SUCCESS_MESSAGE)

    def handle_action(self, param):
        """This function gets current action identifier and calls member function of its own to handle the action.

        :param param: dictionary which contains information about the actions to be executed
        :return: status success/failure
        """

        # Dictionary mapping each action with its corresponding actions
        action_mapping = {
            "test_asset_connectivity": self._test_asset_connectivity,
            "get_report": self._get_report,
            "decode_url": self._decode_url,
            "list_dictionary_items": self._handle_list_dictionary_items,
            "add_dictionary_item": self._handle_add_dictionary_item,
            "remove_dictionary_item": self._handle_remove_dictionary_item,
        }

        action = self.get_action_identifier()

        try:
            run_action = action_mapping[action]
        except Exception:
            raise ValueError(f"action {action} is not supported")

        return run_action(param)

    def finalize(self):
        """This function gets called once all the param dictionary elements are looped over and no more handle_action
        calls are left to be made. It gives the AppConnector a chance to loop through all the results that were
        accumulated by multiple handle_action function calls and create any summary if required. Another usage is
        cleanup, disconnect from remote devices etc.
        """

        return phantom.APP_SUCCESS


if __name__ == "__main__":
    import sys

    import pudb

    pudb.set_trace()
    if len(sys.argv) < 2:
        print("No test json specified as input")
        sys.exit(0)

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))
        connector = CiscoesaConnector()
        connector.print_progress_message = True
        return_value = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(return_value), indent=4))
    sys.exit(0)
