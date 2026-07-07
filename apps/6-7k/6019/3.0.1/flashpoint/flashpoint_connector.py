# --
# File: flashpoint_connector.py
#
# Copyright (c) Flashpoint, 2020-2026
#
# This unpublished material is proprietary to Flashpoint.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Flashpoint.
#
# Licensed under Apache 2.0 (https://www.apache.org/licenses/LICENSE-2.0.txt)
#
# --

import json
import sys
import time

# Phantom App imports
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from flashpoint_consts import *


class RetVal(tuple):
    """Represent the Tuple as a return value."""

    def __new__(cls, val1, val2=None):
        """Recursive call for tuple."""
        return tuple.__new__(RetVal, (val1, val2))


class FlashpointConnector(BaseConnector):
    """Represent a connector module that implements the actions that are provided by the app."""

    def __init__(self):
        """Initialize class variables."""
        # Call the BaseConnectors init first
        super().__init__()

        # Define the global state variable
        self._state = None

        # Define the global variables
        self._base_url = None
        self._api_token = None
        self._x_fp_integration_platform_version = None
        self._x_fp_integration_version = None
        self._wait_timeout_period = None
        self._no_of_retries = None
        self._session_timeout = None

        # Variable to hold the number of attempted retries of REST calls
        self._attempted_retries = 0

    def _process_empty_response(self, response, action_result):
        """Process empty response.

        :param response: response data
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """
        if response.status_code == 200 or response.status_code == 204:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(phantom.APP_ERROR, f"Status code: {response.status_code}. Empty response and no information in the header"),
            None,
        )

    def _process_html_response(self, response, action_result):
        """Process html response.

        :param response: response data
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """
        # An html response, treat it like an error
        status_code = response.status_code

        if 200 <= status_code < 399:
            return RetVal(phantom.APP_SUCCESS, response.text)

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            # Remove the script, style, footer and navigation part from the HTML message
            for element in soup(["script", "style", "footer", "nav"]):
                element.extract()
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except Exception:
            error_text = "Cannot parse error details"

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"

        message = message.replace("{", "{{").replace("}", "}}")

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        """Process json response.

        :param r: response data
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            error_code, error_message = self._get_error_message_from_exception(e)
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR, f"Unable to parse JSON response. Error Code: {error_code}. Error Message: {error_message}"
                ),
                None,
            )

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        message = None
        # Error handling for different type of error responses from server
        if resp_json.get("error") and isinstance(resp_json.get("error"), dict):
            resp_message = resp_json.get("error", {}).get("message", "Error message not found")
            message = "Error from server. Status code: {}. Error code: {}. Error message: {}".format(
                r.status_code, resp_json.get("error", {}).get("code", "Error code not found"), resp_message
            )

        if resp_json.get("detail"):
            detail = resp_json.get("detail", "Error details not found")
            message = f"Error from server. Status code: {r.status_code}. Data from server: {detail}"

        if resp_json.get("message"):
            resp_message = resp_json.get("message", "Error message not found")
            message = f"Error from server. Status code: {r.status_code}. Data from server: {resp_message}"

        # You should process the error returned in the json if none of the above handling happens for error scenario
        if not message:
            resp_text = r.text.replace("{", "{{").replace("}", "}}") if r.text else "Response error text not found"
            message = f"Error from server. Status Code: {r.status_code} Data from server: {resp_text}"

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        """Process API response.

        :param r: response data
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """
        # Store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        # Process each 'Content-Type' of response separately

        # it's not response text, handle an empty response
        if not r.text:
            return self._process_empty_response(r, action_result)

        # Process a json response
        if "json" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result)

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if "html" in r.headers.get("Content-Type", ""):
            return self._process_html_response(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}") if r.text else "Response error text not found"
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _get_error_message_from_exception(self, e):
        """Get appropriate error message from the exception.

        :param e: Exception object
        :return: error message
        """
        error_message = FLASHPOINT_UNKNOWN_ERROR_MESSAGE

        try:
            if e.args:
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_code = FLASHPOINT_ERROR_CODE_MESSAGE
                    error_message = e.args[0]
            else:
                error_code = FLASHPOINT_ERROR_CODE_MESSAGE
                error_message = FLASHPOINT_UNKNOWN_ERROR_MESSAGE
        except Exception:
            error_code = FLASHPOINT_ERROR_CODE_MESSAGE
            error_message = FLASHPOINT_UNKNOWN_ERROR_MESSAGE

        return error_code, error_message

    def _make_rest_call(self, endpoint, action_result, method="get", params=None, data=None):
        """Make the REST call to the app.

        :param endpoint: REST endpoint that needs to appended to the service address
        :param action_result: object of ActionResult class
        :param method: GET/POST/PUT/DELETE/PATCH (Default will be GET)
        :param params: request parameters
        :param data: request body
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        response obtained by making an API call
        """
        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        # Create headers information
        headers = dict()

        headers.update(
            {
                "Authorization": f"Bearer {self._api_token}",
                "Content-Type": "application/json",
                "X-FP-IntegrationPlatform": FLASHPOINT_X_FP_INTEGRATION_PLATFORM,
                "X-FP-IntegrationPlatformVersion": self._x_fp_integration_platform_version,
                "X-FP-IntegrationVersion": self._x_fp_integration_version,
            }
        )

        # Create a URL to connect to Flashpoint
        url = f"{self._base_url}{endpoint}"

        self.debug_print("Making a REST call with provided request parameters")

        try:
            r = request_func(url, params=params, headers=headers, data=data)
        except requests.exceptions.InvalidSchema:
            error_message = f"Error connecting to server. No connection adapters were found for {url}"
            return RetVal(action_result.set_status(phantom.APP_ERROR, error_message), resp_json)
        except requests.exceptions.InvalidURL:
            error_message = f"Error connecting to server. Invalid URL {url}"
            return RetVal(action_result.set_status(phantom.APP_ERROR, error_message), resp_json)
        except Exception as e:
            error_code, error_message = self._get_error_message_from_exception(e)
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR, f"Error connecting to server. Error Code: {error_code}. Error Message: {error_message}"
                ),
                resp_json,
            )

        if self._no_of_retries and r.status_code == 500:
            # Retrying REST call in case of Internal Server Error
            self.save_progress(f"Received Internal Server Error. Retrying API call after {self._wait_timeout_period} seconds")
            self.debug_print(f"Received Internal Server Error. Retrying API call after {self._wait_timeout_period} seconds")
            return self._retry_make_rest_call(action_result, url, headers, request_func, params=params, data=data)

        return self._process_response(r, action_result)

    def _retry_make_rest_call(self, action_result, url, headers, request_func, params=None, data=None):
        """Wait for given wait time period in case of Internal Server Error occurred in the first REST call.

        And, again do REST call for given number of retires(if Internal Server Error continued even after wait).

        :param action_result: object of ActionResult class
        :param url: URL to connect to Flashpoint
        :param headers: headers information for REST call
        :param request_func: request object used for making REST call
        :param params: request parameters
        :param data: request body
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        response obtained by making an API call
        """
        # Increase attempted retry REST call
        self._attempted_retries += 1

        # Wait for given time(in seconds) for getting server up
        time.sleep(self._wait_timeout_period)

        try:
            r = request_func(url, params=params, headers=headers, data=data)
        except Exception as e:
            error_code, error_message = self._get_error_message_from_exception(e)
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR, f"Error connecting to server. Error Code: {error_code}. Error Message: {error_message}"
                ),
                None,
            )

        if r.status_code == 500 and self._attempted_retries < self._no_of_retries:
            # Retrying REST call for given number of retries in case of continuous Internal Server Error
            self.save_progress(f"Received Internal Server Error. Retrying API call after {self._wait_timeout_period} seconds")
            self.debug_print(f"Received Internal Server Error. Retrying API call after {self._wait_timeout_period} seconds")
            return self._retry_make_rest_call(action_result, url, headers, request_func, params=params, data=data)

        return self._process_response(r, action_result)

    def _handle_list_indicators(self, param):
        """Handle the list indicators action.

        :param param: Dictionary of input parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Fetch action parameters
        attributes_types = param.get("attributes_types")
        if attributes_types:
            # check for valid comma-separated list of attribute types
            types = [x.strip() for x in attributes_types.split(",")]
            types = list(filter(None, types))

            if not types:
                return action_result.set_status(phantom.APP_ERROR, FLASHPOINT_INVALID_COMMA_SEPARATED_LIST_ERROR)
            attributes_types = ",".join(types)

        query = param.get("query")
        limit = param.get("limit", FLASHPOINT_PER_PAGE_DEFAULT_LIMIT)

        # Create request parameters
        params = dict()

        if attributes_types:
            params.update({"types": attributes_types.lower()})
        if query:
            params.update({"query": query})

        # Call session scrolling paginator
        ret_val, iocs = self._enable_session_scrolling_paginator(action_result, limit=limit, params=params, flag=True)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add fetched data to action result object
        for ioc in iocs:
            if "Attribute" in list(ioc.keys()):
                action_result.add_data(ioc.get("Attribute"))
            else:
                action_result.add_data(ioc)

        # Create summary
        summary = action_result.update_summary({})
        summary["total_iocs"] = action_result.get_data_size()

        # Return success
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_search_indicators(self, param):
        """Handle the search indicators action.

        :param param: Dictionary of input parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Fetch action parameters
        attribute_type = param["attribute_type"]
        attribute_value = param["attribute_value"]

        limit = param.get("limit", FLASHPOINT_PER_PAGE_DEFAULT_LIMIT)

        attribute_type = attribute_type.strip().lower()
        # Create request parameters
        params = dict()
        if attribute_type.lower() == "url":
            # if url value is passed without inverted comma, then, the server responds with Internal Server Error.
            # so for ad-hoc fixation we are passing url value within inverted comma for avoiding unnecessary Internal Server Error
            params.update({"search_fields": f'{attribute_type}=="{attribute_value}"'})
        else:
            params.update({"search_fields": f"{attribute_type}=={attribute_value}"})

        # Make rest call
        ret_val, iocs = self._enable_session_scrolling_paginator(action_result, limit=limit, params=params, flag=True)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add fetched data to action result object
        for ioc in iocs:
            if "Attribute" in list(ioc.keys()):
                action_result.add_data(ioc.get("Attribute"))
            else:
                action_result.add_data(ioc)

        # Create summary
        summary = action_result.update_summary({})
        summary["total_iocs"] = action_result.get_data_size()

        # Return success
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_run_query(self, param):
        """Handle the run query action.

        :param param: Dictionary of input parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Fetch action parameters
        query = param["query"]
        limit = param.get("limit", FLASHPOINT_PER_PAGE_DEFAULT_LIMIT)

        # Create request parameters
        params = dict()
        params.update({"query": query})

        # Make rest call
        ret_val, results = self._enable_session_scrolling_paginator(action_result, limit=limit, params=params)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add fetched data to action result object
        for result in results:
            action_result.add_data(result)

        # Create summary
        summary = action_result.update_summary({})
        summary["total_results"] = action_result.get_data_size()

        # Return success
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_compromised_credentials(self, param):
        """Handle the get compromised credentials action.

        :param param: Dictionary of input parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Fetch action parameters
        query_filter = param.get("filter")
        limit = param.get("limit", FLASHPOINT_PER_PAGE_DEFAULT_LIMIT)

        # Create request parameters
        params = dict()
        query = "+basetypes:credential-sighting{}".format(query_filter if query_filter else "")

        params.update({"query": query})

        # Make rest call
        ret_val, results = self._enable_session_scrolling_paginator(action_result, limit=limit, params=params)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add fetched data to action result object
        for result in results:
            action_result.add_data(result)

        # Create summary
        summary = action_result.update_summary({})
        summary["total_results"] = action_result.get_data_size()

        # Return success
        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_params_endpoint(self, action_result, limit=None, flag=False, params=None):
        """Preprocess the input parameters for the paginator.

        :param action_result: object of ActionResult class
        :param limit: maximum number of results to be fetched
        :param flag: If flag value is True, this paginator work for indicators APIs; else it's works for all search APIs
        :param params: request parameters

        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR), params, endpoint
        """
        # Validate the 'limit' action parameter
        limit = self._validate_integers(action_result, limit, FLASHPOINT_ACTION_LIMIT_KEY)
        if limit is None:
            return action_result.get_status(), None, None, None

        # Define per page limit
        page_limit = FLASHPOINT_PER_PAGE_DEFAULT_LIMIT

        if limit and limit <= FLASHPOINT_PER_PAGE_DEFAULT_LIMIT:
            page_limit = limit

        if params:
            params.update({"limit": page_limit})
        else:
            params = dict()
            params.update({"limit": page_limit})

        if flag:
            # This block is used for indicators simple APIs

            # Enable the session scroll for the first time
            params.update({"scroll": True})
            endpoint = FLASHPOINT_INDICATORS_ENDPOINT
        else:
            # This block will use for all search APIs

            # Enable the session scroll for the first time
            params.update({"scroll": f"{self._session_timeout}m"})
            endpoint = FLASHPOINT_ALL_SEARCH_ENDPOINT

        return phantom.APP_SUCCESS, params, endpoint, limit

    def _enable_session_scrolling_paginator(self, action_result, limit=None, flag=False, params=None):
        """Enable session scrolling for indicators and search APIs and fetch the results based on provided request parameters.

        :param action_result: object of ActionResult class
        :param limit: maximum number of results to be fetched
        :param flag: If flag value is True, this paginator work for indicators APIs; else it's works for all search APIs
        :param params: request parameters

        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR), fetched results of IoCs or all search results
        """
        total_items = list()
        endpoint = ""
        scroll_id = None

        # initial processor for paginator which creates endpoint parameters
        ret_val, params, endpoint, limit = self._get_params_endpoint(action_result, limit, flag, params)
        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        self.debug_print("Making the first REST call to enable session scrolling")

        # Make rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, params=params)
        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        # Response processing based on APIs
        items, scroll_id = self._paginator_response_processing(response, flag)

        if not items:
            # Disable session scrolling before returning from the initial paginator
            ret_val = self._disable_session_scrolling(action_result, scroll_id, flag)
            if phantom.is_fail(ret_val):
                return action_result.get_status(), None

            if items is None:
                return action_result.set_status(phantom.APP_ERROR, "No data found"), None

            return phantom.APP_SUCCESS, []

        total_items.extend(items)

        if limit and len(total_items) >= limit:
            # Disable session scrolling before returning from the initial paginator
            ret_val = self._disable_session_scrolling(action_result, scroll_id, flag)
            if phantom.is_fail(ret_val):
                return action_result.get_status(), None

            return phantom.APP_SUCCESS, total_items[:limit]

        # Limit for remaining results fetching
        limit_for_further_paginator = limit - FLASHPOINT_PER_PAGE_DEFAULT_LIMIT

        ret_val, items = self._further_pagination(action_result, limit=limit_for_further_paginator, scroll_id=scroll_id, flag=flag)
        if phantom.is_fail(ret_val):
            # Disable session scrolling before returning from the initial paginator
            self._disable_session_scrolling(action_result, scroll_id, flag)
            return action_result.get_status(), None

        total_items.extend(items)

        # Return success with fetched all data
        return phantom.APP_SUCCESS, total_items

    def _get_scrolling_endpoint(self, flag):
        """Determine endpoint for paginator.

        :param flag: If flag value is True, this will return indicators scrolling endpoint; else it will return search scrolling endpoint

        :return: scrolling endpoint
        """
        # Define session scroll endpoint
        if flag:
            # This block is used for indicators simple APIs
            endpoint = FLASHPOINT_SIMPLIFIED_INDICATORS_SCROLL_ENDPOINT
        else:
            # This block is used for all search APIs
            endpoint = f"{FLASHPOINT_ALL_SEARCH_SCROLL_ENDPOINT}?scroll={self._session_timeout}m"

        return endpoint

    def _further_pagination(self, action_result, limit, scroll_id, flag):
        """Fetch IoCs or all search results using scroll ID.

        :param action_result: object of ActionResult class
        :param limit: maximum number of results to be fetched
        :param scroll_id: it will use to fetch results by scrolling
        :param flag: If flag value is True, this further paginator work for indicators APIs; else it's works for all search APIs

        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR), fetched results of IoCs or all search results
        """
        total_items = list()

        # If not scroll id, return success with fetched data
        if not scroll_id:
            return phantom.APP_SUCCESS, total_items

        # Create request data for session scrolling
        data = {"scroll_id": scroll_id}

        self.debug_print("Making a further rest call for getting remaning data using fetched scroll ID")
        while True:
            # Make rest call
            ret_val, response = self._make_rest_call(self._get_scrolling_endpoint(flag), action_result, method="post", data=json.dumps(data))
            if phantom.is_fail(ret_val):
                return action_result.get_status(), None

            # Response processing based on APIs
            items, _ = self._paginator_response_processing(response, flag)

            if items is None:
                return action_result.set_status(phantom.APP_ERROR, "No data found"), None

            total_items.extend(items)

            # Fetched all data and fetched items list is empty and not None
            if not items:
                self.debug_print("Fetched all data and fetched items list is empty and not None")
                break

            if limit and len(total_items) >= limit:
                # Disable session scrolling before returning from the further paginator
                ret_val = self._disable_session_scrolling(action_result, scroll_id, flag)
                if phantom.is_fail(ret_val):
                    return action_result.get_status(), None

                return phantom.APP_SUCCESS, total_items[:limit]

        # Disable session scrolling before returning from the further paginator
        ret_val = self._disable_session_scrolling(action_result, scroll_id, flag)
        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        # Return success with fetched data
        return phantom.APP_SUCCESS, total_items

    def _paginator_response_processing(self, response, flag):
        """Get IoCs or all search results from the response of make rest call.

        :param response: response of make rest call
        :param flag: If flag value is True, this paginator response processor work for indicators APIs; else it's works for all search APIs
        :return: IoCs or all search results, scroll ID
        """
        scroll_id = None
        total_items = None

        if flag:
            # IoCs results
            total_items = response.get("results")
            scroll_id = response.get("scroll_id")
        else:
            # All search results
            total_items = response.get("hits", {}).get("hits")
            scroll_id = response.get("_scroll_id")

        # Return IoCs or all search results with scroll ID
        return total_items, scroll_id

    def _disable_session_scrolling(self, action_result, scroll_id, flag=False):
        """Disable session scrolling for indicators and search APIs.

        :param action_result: object of ActionResult class
        :param scroll_id: session scroll id to be disabled.
        :param flag: If flag value is True, this paginator finalize work for indicators APIs; else it's works for all search APIs

        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """
        if not scroll_id:
            self.debug_print("Scroll session is not available")
            return phantom.APP_SUCCESS

        endpoint = ""
        data = {"scroll_id": scroll_id}

        if flag:
            # This block is used for indicators simple APIs
            endpoint = FLASHPOINT_SIMPLIFIED_INDICATORS_SCROLL_ENDPOINT
        else:
            # This block is used for all search APIs
            endpoint = FLASHPOINT_ALL_SEARCH_SCROLL_ENDPOINT

        self.debug_print("Make a rest call to disable scroll session")

        # Make rest call
        ret_val, _ = self._make_rest_call(endpoint, action_result, method="delete", data=json.dumps(data))

        if phantom.is_fail(ret_val):
            # If session already disabled
            if FLASHPOINT_ALREADY_DISABLE_SESSION_SCROLL_ERROR_MESSAGE in action_result.get_message():
                self.debug_print("Session is already disabled")
                return phantom.APP_SUCCESS
            return action_result.get_status()

        self.debug_print("Successfully disabled the scroll session")
        return phantom.APP_SUCCESS

    def _paginator_using_skip(self, action_result, endpoint, limit=None, params=None):
        """Fetch reports data using skip pagination.

        :param action_result: object of ActionResult class
        :param endpoint: REST endpoint that needs to appended to the service address
        :param limit: maximum number of results to be fetched
        :param params: request parameters

        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR), total reports
        """
        total_reports = list()
        skip = 0

        # Define per page limit
        page_limit = FLASHPOINT_PER_PAGE_DEFAULT_LIMIT

        if limit and limit <= page_limit:
            page_limit = limit

        if params:
            params.update({"limit": page_limit})
        else:
            params = dict()
            params.update({"limit": page_limit})

        while True:
            params.update({"skip": skip})

            # Make rest call
            ret_val, response = self._make_rest_call(endpoint, action_result, params=params)

            if phantom.is_fail(ret_val):
                return action_result.get_status(), None

            # Fetch data from response
            reports = response.get("data")
            if reports is None:
                return action_result.set_status(phantom.APP_ERROR, "No data found"), None

            total_reports.extend(reports)

            if limit and len(total_reports) >= limit:
                return phantom.APP_SUCCESS, total_reports[:limit]

            total = response.get("total")
            if len(total_reports) >= total:
                return phantom.APP_SUCCESS, total_reports

            skip += FLASHPOINT_PER_PAGE_DEFAULT_LIMIT

        # Return success with total reports
        return phantom.APP_SUCCESS, total_reports

    def _handle_test_connectivity(self, param):
        """Validate the asset configuration for connectivity using supplied configuration.

        :param param: Dictionary of input parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """
        self.debug_print(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Trying to fetch IoCs using indicators endpoint")

        # Fetch single indicator(IoC) for the test connectivity
        param = dict()
        param.update({"limit": 1})

        # Make rest call
        ret_val, _ = self._make_rest_call(FLASHPOINT_INDICATORS_ENDPOINT, action_result, params=param)

        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed")
            return action_result.get_status()

        # Return success
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _fetch_reports(self, action_result, endpoint, limit):
        """Fetch reports data.

        :param action_result: object of ActionResult class
        :param endpoint: REST endpoint that needs to appended to the service address
        :param limit: maximum number of results to be fetched

        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """
        # Validate the 'limit' action parameter
        limit = self._validate_integers(action_result, limit, FLASHPOINT_ACTION_LIMIT_KEY)
        if limit is None:
            return action_result.get_status()

        # Call paginator to fetch data
        ret_val, reports = self._paginator_using_skip(action_result, endpoint, limit)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Process report data
        reports = self._process_report_data(data=reports)

        # Add fetched data to action result object
        for report in reports:
            action_result.add_data(report)

        # Return success
        return phantom.APP_SUCCESS

    def _handle_list_reports(self, param):
        """Handle the list reports action.

        :param param: Dictionary of input parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Fetch action parameters
        limit = param.get("limit", FLASHPOINT_PER_PAGE_DEFAULT_LIMIT)

        # Fetch reports data
        ret_val = self._fetch_reports(action_result, FLASHPOINT_LIST_REPORTS_ENDPOINT, limit)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Create summary
        summary = action_result.update_summary({})
        summary["total_reports"] = action_result.get_data_size()

        # Return success
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_related_reports(self, param):
        """Handle the list related reports action.

        :param param: Dictionary of input parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Fetch action parameters
        report_id = param["report_id"]

        limit = param.get("limit", FLASHPOINT_PER_PAGE_DEFAULT_LIMIT)

        # Fetch reports
        ret_val = self._fetch_reports(action_result, FLASHPOINT_LIST_RELATED_REPORTS_ENDPOINT.format(report_id=report_id), limit)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Create summary
        summary = action_result.update_summary({})
        summary["total_related_reports"] = action_result.get_data_size()

        # Return success
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_report(self, param):
        """Handle the get report action.

        :param param: Dictionary of input parameters
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Fetch action parameters
        report_id = param["report_id"]

        # Make rest call
        ret_val, report = self._make_rest_call(FLASHPOINT_GET_REPORT_ENDPOINT.format(report_id=report_id), action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Process report data
        reports = self._process_report_data(data=[report])

        # Add fetched data to action result object
        action_result.add_data(reports[0])

        # Return success
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully fetched report")

    def _process_report_data(self, data):
        """Process reports data and add the processed body and processed summary.

        :param data: reports data
        :return: processed reports data
        """
        for i, item in enumerate(data):
            # Process report body
            body = item.get("body")
            if body:
                try:
                    soup = BeautifulSoup(body, "html.parser")
                    body_text = soup.text
                    split_lines = body_text.split("\n")
                    split_lines = [x.strip() for x in split_lines if x.strip()]
                    body_text = "\n".join(split_lines)
                except Exception:
                    body_text = body

                data[i].update({"processed_body": body_text})
            else:
                data[i].update({"body": body})
                data[i].update({"processed_body": body})

            # Process report summary
            summary = item.get("summary")
            if summary:
                try:
                    soup = BeautifulSoup(summary, "html.parser")
                    summary_text = soup.text
                    split_lines = summary_text.split("\n")
                    split_lines = [x.strip() for x in split_lines if x.strip()]
                    summary_text = "\n".join(split_lines)
                except Exception:
                    summary_text = summary

                data[i].update({"processed_summary": summary_text})
            else:
                data[i].update({"summary": summary})
                data[i].update({"processed_summary": summary})

        # Return processed data
        return data

    def _validate_integers(self, action_result, parameter, key, allow_zero=False):
        """Check if the provided input parameter value is a non-zero positive integer and returns the integer value of the parameter itself.

        :param action_result: Action result object
        :param parameter: input parameter
        :return: integer value of the parameter
        """
        try:
            if not float(parameter).is_integer():
                action_result.set_status(phantom.APP_ERROR, FLASHPOINT_ERROR_VALID_INT_MESSAGE.format(parameter=key))
                return None

            parameter = int(parameter)
            if parameter <= 0:
                if allow_zero:
                    if parameter < 0:
                        action_result.set_status(phantom.APP_ERROR, FLASHPOINT_LIMIT_VALIDATION_ALLOW_ZERO_MESSAGE.format(parameter=key))
                        return None
                else:
                    action_result.set_status(phantom.APP_ERROR, FLASHPOINT_LIMIT_VALIDATION_MESSAGE.format(parameter=key))
                    return None
        except Exception:
            error_text = (
                FLASHPOINT_LIMIT_VALIDATION_ALLOW_ZERO_MESSAGE.format(parameter=key)
                if allow_zero
                else FLASHPOINT_LIMIT_VALIDATION_MESSAGE.format(parameter=key)
            )
            action_result.set_status(phantom.APP_ERROR, error_text)
            return None
        return parameter

    def handle_action(self, param):
        """Get current action identifier and call member function of its own to handle the action.

        :param param: dictionary which contains information about the actions to be executed
        :return: status success/failure
        """
        # Get the action that we are supposed to execute for this App Run
        action = self.get_action_identifier()
        action_execution_status = phantom.APP_SUCCESS

        self.debug_print("action_id", self.get_action_identifier())

        # Dictionary mapping each action with its corresponding actions
        action_mapping = {
            "test_connectivity": self._handle_test_connectivity,
            "list_reports": self._handle_list_reports,
            "get_report": self._handle_get_report,
            "list_related_reports": self._handle_list_related_reports,
            "get_compromised_credentials": self._handle_get_compromised_credentials,
            "run_query": self._handle_run_query,
            "list_indicators": self._handle_list_indicators,
            "search_indicators": self._handle_search_indicators,
        }

        if action in list(action_mapping.keys()):
            action_function = action_mapping[action]
            action_execution_status = action_function(param)

        return action_execution_status

    def initialize(self):
        """Initialize the global variables with its value and validate it."""
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # Get the asset config
        config = self.get_config()

        self._base_url = config["base_url"]
        self._api_token = config["api_token"]
        self._x_fp_integration_platform_version = self.get_product_version()
        self._x_fp_integration_version = self.get_app_json().get("app_version")

        # Validate the 'wait_timeout_period' config parameter
        self._wait_timeout_period = self._validate_integers(
            self, config.get("wait_timeout_period", FLASHPOINT_DEFAULT_WAIT_TIMEOUT_PERIOD), FLASHPOINT_CONFIG_WAIT_TIMEOUT_PERIOD_KEY
        )
        if self._wait_timeout_period is None:
            return self.get_status()

        # Validate the 'no_of_retries' config parameter
        self._no_of_retries = self._validate_integers(
            self, config.get("no_of_retries", FLASHPOINT_NUMBER_OF_RETRIES), FLASHPOINT_CONFIG_NO_OF_RETRIES_KEY, True
        )
        if self._no_of_retries is None:
            return self.get_status()

        # Validate the 'session_timeout' config parameter
        self._session_timeout = self._validate_integers(
            self, config.get("session_timeout", FLASHPOINT_SESSION_TIMEOUT), FLASHPOINT_CONFIG_SESSION_TIMEOUT_KEY
        )
        if self._session_timeout is None:
            return self.get_status()

        if self._session_timeout > 60:
            return self.set_status(phantom.APP_ERROR, FLASHPOINT_ERROR_SESSION_TIMEOUT_VALUE)

        return phantom.APP_SUCCESS

    def finalize(self):
        """Perform some final operations or clean up operations.

        :return: status (success/failure)
        """
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)

        return phantom.APP_SUCCESS


if __name__ == "__main__":
    import argparse

    import pudb

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)
    argparser.add_argument("-v", "--verify", action="store_true", help="verify", required=False, default=False)

    args = argparser.parse_args()
    session_id = None
    verify = args.verify

    username = args.username
    password = args.password

    if username is not None and password is None:
        # User specified a username but not a password, so ask
        import getpass

        password = getpass.getpass("Password: ")

    if username and password:
        try:
            login_url = FlashpointConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=FLASHPOINT_DEFAULT_REQUEST_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=FLASHPOINT_DEFAULT_REQUEST_TIMEOUT)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = FlashpointConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
