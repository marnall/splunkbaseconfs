# File: qualys_ssllabs_connector.py
#
# Copyright (c) 2016-2025 Splunk Inc.
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
# Phantom imports
import time
from re import sub

import phantom.app as phantom
import requests
import simplejson as json
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# THIS Connector imports
from qualys_ssllabs_consts import *


class SslLabsConnector(BaseConnector):
    # actions supported by this script
    ACTION_ID_RUN_QUERY = "run_query"

    def __init__(self):
        """ """

        self.__id_to_name = {}

        # Call the BaseConnectors init first
        super().__init__()

    def initialize(self):
        """Called once for every action, all member initializations occur here"""

        config = self.get_config()
        self._verify = config[phantom.APP_JSON_VERIFY]
        # Get the Base URL from the asset config and so some cleanup
        self._base_url = config.get("base_url", QUALYS_SSLLABS_BASE_URL)
        if self._base_url.endswith("/"):
            self._base_url = self._base_url[:-1]

        # The host member extacts the host from the URL, is used in creating status messages
        self._host = self._base_url[self._base_url.find("//") + 2 :]

        # The headers, initialize them here once and use them for all other REST calls
        self._headers = {"Accept": "application/json"}

        # The common part after the base url, but before the specific endpoint
        # Intiliazed here and used on every REST endpoint calls
        self._api_uri = QUALYS_SSLLABS_BASE_API
        if self._api_uri.endswith("/"):
            self._api_uri = self._api_uri[:-1]
        return phantom.APP_SUCCESS

    def _get_error_details(self, resp_json):
        """Function that parses the error json recieved from the device and placed into a json"""

        error_details = {"message": "Not Found", "detail": "Not supplied"}

        if not resp_json:
            return error_details

        error_info = resp_json.get("error")

        if not error_info:
            return error_details

        if "message" in error_info:
            error_details["message"] = error_info["message"]

        if "detail" in error_info:
            error_details["detail"] = error_info["detail"]

        return error_details

    def _make_rest_call(self, endpoint, action_result, headers=None, params=None, data=None, method="get"):
        """Function that makes the REST call to the device

        This is a generic function that can be called from various action handlers.
        """
        if not headers:
            headers = {}

        # Create the headers
        headers.update(self._headers)

        if method in ["put", "post"]:
            headers.update({"Content-Type": "application/json"})

        resp_json = None

        # get or post or put, whatever the caller asked us to use, if not specified the default will be 'get'
        request_func = getattr(requests, method)

        # handle the error in case the caller specified a non-existant method
        if not request_func:
            action_result.set_status(phantom.APP_ERROR, ERR_API_UNSUPPORTED_METHOD, method=method)
        # Make the call
        try:
            r = request_func(
                self._base_url + self._api_uri + endpoint,
                # The complete url is made up of the base_url, the api url and the endpiont
                data=json.dumps(data) if data else None,
                # the data, converted to json string format if present, else just set to None
                headers=headers,  # The headers to send in the HTTP call
                verify=self._verify,  # should cert verification be carried out?
                params=params,
            )  # uri parameters if any
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, ERR_SERVER_CONNECTION, e), resp_json

        # Try a json parse, since most REST API's give back the data in json,
        # if the device does not return JSONs, then need to implement parsing them some other manner
        try:
            resp_json = r.json()
        except Exception as e:
            # r.text is guaranteed to be NON None, it will be empty, but not None
            msg_string = ERR_JSON_PARSE.format(raw_text=e)
            return action_result.set_status(phantom.APP_ERROR, msg_string), resp_json

        # Handle any special HTTP error codes here, many devices return an HTTP error code like 204.
        # The requests module treats these as error,
        # so handle them here before anything else, uncomment the following lines in such cases

        # Handle/process any errors that we get back from the device
        if r.status_code == 200:
            # Success
            return phantom.APP_SUCCESS, resp_json

        # 400 - invocation error (e.g., invalid parameters)
        # 429 - client request rate too high or too many new assessments too fast
        # 500 - internal error
        # 503 - the service is not available (e.g., down for maintenance)
        # 529 - the service is overloaded

        # Failure
        action_result.add_data(resp_json)

        details = json.dumps(resp_json).replace("{", "").replace("}", "")

        return (action_result.set_status(phantom.APP_ERROR, ERR_FROM_SERVER.format(status=r.status_code, detail=details)), resp_json)

    def _test_connectivity(self, param):
        """Function that handles the test connectivity action, it is much simpler than other action handlers."""

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        # set the endpoint
        endpoint = "/info"
        # Progress
        self.save_progress(USING_BASE_URL, base_url=self._base_url, api_uri=self._api_uri, endpoint=endpoint)

        # Action result to represent the call
        action_result = ActionResult()

        # Progress message, since it is test connectivity, it pays to be verbose
        self.save_progress(QUALYS_SSLLABS_MSG_GET_INFO)

        # Make the rest endpoint call
        ret_val, response = self._make_rest_call(endpoint, action_result, params="")

        # Process errors
        if phantom.is_fail(ret_val):
            # Dump error messages in the log
            self.debug_print(action_result.get_message())

            # Set the status of the complete connector result
            self.set_status(phantom.APP_ERROR, action_result.get_message())

            # Append the message to display
            self.append_to_message(ERR_CONNECTIVITY_TEST)

            # return error
            return phantom.APP_ERROR

        try:
            self.save_progress("engineVersion: {}".format(response["engineVersion"]))
            self.save_progress("criteriaVersion: {}".format(response["criteriaVersion"]))
            self.save_progress("clientMaxAssessments: {}".format(response["clientMaxAssessments"]))
            self.save_progress("currentAssessments: {}".format(response["currentAssessments"]))
            self.save_progress("maxAssessments: {}".format(response["maxAssessments"]))
        except Exception as ex:
            self.debug_print(f"Exception: {ex}")
            pass

        # Set the status of the connector result
        return self.set_status_save_progress(phantom.APP_SUCCESS, SUCC_CONNECTIVITY_TEST)

    def _poll_status(self, endpoint, action_result, params={}):
        polling_attempt = 0
        timeout = POLL_TIMEOUT_MINS
        max_polling_attempts = (int(timeout) * 60) / SLEEP_SECS

        ret_val, response = phantom.APP_ERROR, None

        while polling_attempt < max_polling_attempts:
            polling_attempt += 1
            self.save_progress(f"Polling attempt {polling_attempt} of {max_polling_attempts}")
            ret_val, response = self._make_rest_call(endpoint, action_result, params=params)

            if phantom.is_fail(ret_val):
                action_result.append_to_message(str(response))
                self.debug_print(action_result.get_message())
                action_result.set_summary(response)
                self.set_status(phantom.APP_ERROR)
                return ret_val, response

            if response.get("status") != "READY":  # report is not ready, go to polling mode
                self.save_progress("Status: {}".format(response.get("status")))
                time.sleep(SLEEP_SECS)
            else:
                return ret_val, response

        self.save_progress("Reached max polling attempts.")
        action_result.append_to_message("Reached max polling attempts.")
        self.debug_print(action_result.get_message())
        action_result.set_summary(response)
        self.set_status(phantom.APP_ERROR)
        return ret_val, response

    def _run_query(self, param):
        """Action handler for the 'run query' action"""

        # This is an action that needs to be represented by the ActionResult object
        # So create one and add it to 'self' (i.e. add it to the BaseConnector)
        # When the action_result is created this way, the parameter is also passed.
        # Other things like the summary, data and status is set later on.
        action_result = self.add_action_result(ActionResult(dict(param)))
        # Endpoint
        endpoint = "/analyze"
        # Progress
        self.save_progress(USING_BASE_URL, base_url=self._base_url, api_uri=self._api_uri, endpoint=endpoint)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        # parameters here
        # host - hostname; required.
        # publish - set to "on" if assessment results should be published on the public results boards; optional,
        # defaults to "off".
        # startNew - if set to "on" then cached assessment results are ignored and a new assessment is started.
        # However, if there's already an assessment in progress, its status is delivered instead.
        # This parameter should be used only once to initiate a new assessment; further invocations
        # should omit it to avoid causing an assessment loop.
        # fromCache - always deliver cached assessment reports if available; optional, defaults to "off".
        # This parameter is intended for API consumers that don't want to wait for assessment results.
        # Can't be used at the same time as the startNew parameter.
        # maxAge - maximum report age, in hours, if retrieving from cache (fromCache parameter set).
        # all - by default this call results only summaries of individual endpoints. If this parameter is set to "on",
        # full information will be returned. If set to "done", full information will be returned only if the
        # assessment is complete (status is READY or ERROR).
        # ignoreMismatch - set to "on" to proceed with assessments even when the server certificate doesn't match
        # the assessment hostname. Set to off by default. Please note that this parameter is ignored
        # if a cached report is returned.
        request_params = {}

        # determine if we start by checking for existing cached results and
        # then running a new query or just with a new query
        if param.get("start_new", "on") == "on":
            request_params["host"] = param.get("host").strip()
            request_params["publish"] = param.get("publish", "off")
            request_params["startNew"] = "on"
            request_params["all"] = param.get("return_all_data", "off")
            request_params["ignoreMismatch"] = param.get("ignore_mismatch", "off")
        else:
            request_params["host"] = param.get("host").strip()
            request_params["publish"] = param.get("publish", "off")
            request_params["fromCache"] = "on"
            if param.get("max_age"):
                # fix maxAge, if its set to 0 it sends Qualys into an infinite loop
                try:
                    if int(param.get("max_age")) <= 0:
                        request_params["maxAge"] = str(QUALYS_SSLLABS_MAX_AGE)
                    else:
                        request_params["maxAge"] = str(param.get("max_age"))
                except Exception as ex:
                    self.debug_print(f"Exception: {ex}")
                    self.debug_print(f"Exception on maxAge value, setting to default SSLLABS_MAX_AGE : {QUALYS_SSLLABS_MAX_AGE}")
                    request_params["maxAge"] = str(QUALYS_SSLLABS_MAX_AGE)
            request_params["all"] = param.get("return_all_data", "off")

        if param.get("return_all_data", "off") == "off":
            del request_params["all"]

        # strip formatting out of host that shouldnt be there.
        if request_params["host"].endswith("/"):
            request_params["host"] = request_params["host"][:-1]
        request_params["host"] = sub(r"https{0,1}:\/{0,2}", "", request_params["host"])

        # Make the rest call, note that if we try for cached and its not there,
        # it will automatically go to start a new analysis.
        # unless specified start a new as above.
        ret_val, response = self._make_rest_call(endpoint, action_result, params=request_params)

        # Process errors
        if (
            phantom.is_fail(ret_val)
            or response is None
            or response is False
            or response.get("status") is None
            or ("errors" in response.keys())
            or response.get("status") == "ERROR"
        ):
            self.debug_print(f"FAILURE: Found in the app response.\nResponse: {response}")
            if response is None:
                action_result.set_summary({"Error": "No response from server"})
                self.set_status(phantom.APP_ERROR)
                return phantom.APP_ERROR
            else:
                action_result.append_to_message(str(response))
                action_result.set_summary(response)
                self.set_status(phantom.APP_ERROR)
                return phantom.APP_ERROR

        elif response.get("status") != "READY":  # report is not ready, go to polling mode
            if "startNew" in request_params.keys():
                del request_params["startNew"]
            ret_val, response = self._poll_status(endpoint, action_result, params=request_params)

            if (
                phantom.is_fail(ret_val)
                or response is None
                or response is False
                or response.get("status") is None
                or ("errors" in response.keys())
                or response.get("status") == "ERROR"
            ):
                self.save_progress("Reached max polling attempts.")
                action_result.append_to_message("Reached max polling attempts.")
                return phantom.APP_ERROR
            else:
                # Set the summary and response data
                action_result.add_data(response)
                action_result.set_summary({"total_endpoints": len(response.get("endpoints", []))})
                # Set the Status
                return action_result.set_status(phantom.APP_SUCCESS)

        else:
            # Set the summary and response data
            action_result.add_data(response)
            action_result.set_summary({"total_endpoints": len(response.get("endpoints", []))})
            # Set the Status
            return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        """Function that handles all the actions"""
        # Get the action that we are supposed to carry out, set it in the connection result object
        action = self.get_action_identifier()
        # Intialize it to success
        ret_val = phantom.APP_SUCCESS
        # Bunch if if..elif to process actions
        if action == self.ACTION_ID_RUN_QUERY:
            ret_val = self._run_query(param)
        elif action == phantom.ACTION_ID_TEST_ASSET_CONNECTIVITY:
            ret_val = self._test_connectivity(param)

        return ret_val


if __name__ == "__main__":
    """ Code that is executed when run in standalone debug mode
    for .e.g:
    python2.7 ./qualys_ssllabs_connector.py /tmp/qualys_ssllabs_test.json
        """

    # Imports
    import sys

    import pudb

    # Breakpoint at runtime
    pudb.set_trace()

    # The first param is the input json file
    with open(sys.argv[1]) as f:
        # Load the input json file
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=" " * 4))

        # Create the connector class object
        connector = SslLabsConnector()

        # Se the member vars
        connector.print_progress_message = True

        # Call BaseConnector::_handle_action(...) to kickoff action handling.
        ret_val = connector._handle_action(json.dumps(in_json), None)

        # Dump the return value
        print(ret_val)

    sys.exit(0)
