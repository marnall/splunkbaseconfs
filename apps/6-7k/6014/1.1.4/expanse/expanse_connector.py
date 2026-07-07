# File: expanse_connector.py
#
# Copyright (c) Expanse, 2020-2025
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
# Python 3 Compatibility imports

import base64
import ipaddress
import json
from datetime import datetime, timedelta

# Phantom App imports
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from expanse_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class ExpanseConnector(BaseConnector):
    def __init__(self):
        super().__init__()

        self._state = None

        self._base_url = "https://expander.expanse.co"
        self._token = None
        self._jwt = None

    def _get_error_message_from_exception(self, e):
        """
        Get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """
        error_code = None
        error_msg = ERR_MSG_UNAVAILABLE

        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                elif len(e.args) == 1:
                    error_msg = e.args[0]
        except:
            pass

        if not error_code:
            error_text = f"Error Message: {error_msg}"
        else:
            error_text = f"Error Code: {error_code}. Error Message: {error_code}"

        return error_text

    def _is_ip(self, input_ip_address):
        """
        Function that checks given address and returns True if address is valid IPv4 or IPV6 address.

        :param input_ip_address: IP address
        :return: status (success/failure)
        """

        try:
            ipaddress.ip_address(input_ip_address)
        except Exception:
            return False

        return True

    def _process_empty_response(self, response, action_result):
        if response.status_code in [STATUS_CODE_200, STATUS_CODE_204]:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(
                phantom.APP_ERROR, f"Status Code: {response.status_code}. Empty response and no information in the header."
            ),
            None,
        )

    def _process_html_response(self, response, action_result):
        # An html response, treat it like an error
        status_code = response.status_code

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

        if not error_text:
            error_text = "Empty response and no information received"

        message = f"Status Code: {status_code}. Data from server: {error_text}"
        message = message.replace("{", "{{").replace("}", "}}")

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, response, action_result):
        # Try a json parse
        try:
            resp_json = response.json()
        except Exception as e:
            error_msg = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. Error: {error_msg}"), None)

        # Please specify the status codes here
        if STATUS_CODE_200 <= response.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {} Data from server: {}".format(
            response.status_code, response.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, response, action_result):
        # store the r_text in debug data
        # it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": response.status_code})
            action_result.add_debug_data({"r_text": response.text})
            action_result.add_debug_data({"r_headers": response.headers})

        # Process each 'Content-Type' of response separately

        # Process a json response
        if "json" in response.headers.get("Content-Type", ""):
            return self._process_json_response(response, action_result)

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        elif "html" in response.headers.get("Content-Type", ""):
            return self._process_html_response(response, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        elif not response.text:
            return self._process_empty_response(response, action_result)

        # everything else is actually an error at this point
        else:
            message = "Can't process response from server. Status Code: {} Data from server: {}".format(
                response.status_code, response.text.replace("{", "{{").replace("}", "}}")
            )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, method="get", **kwargs):
        config = self.get_config()
        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        # Create a URL to connect to
        url = f"{self._base_url}{endpoint}"

        try:
            r = request_func(url, verify=config.get("verify_server_cert", False), **kwargs)
        except Exception as e:
            error_msg = self._get_error_message_from_exception(e)
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {error_msg}"), resp_json)

        return self._process_response(r, action_result)

    def _fetch_jwt(self, action_result, config):
        # Returns a new JWT using the included token if a no valid JWT exists
        self._token = config.get("Token")
        if self._jwt is not None or (self._state.get("jwt") is not None and self._state.get("jwt_exp") is not None):
            # JWT exists and may be valid
            if self._jwt is not None:
                # should be fresh
                return phantom.APP_SUCCESS, self._jwt
            if self._state.get("jwt") is not None and self._state.get("jwt_exp") is not None:
                # check if jwt ts is less than 2 hour, if not, renew
                now_epoch = int(datetime.today().strftime("%s"))
                if now_epoch > self._state.get("jwt_exp"):
                    # jwt is old, clear state and retry
                    self._jwt = None
                    del self._state["jwt"]
                    del self._state["jwt_exp"]
                    return self._fetch_jwt(action_result, config)
                else:
                    self._jwt = self._state.get("jwt")
                    return phantom.APP_SUCCESS, self._jwt
        elif self._token is not None:
            # JWT does not exist, but we can generate a new one
            try:
                return self._request_new_jwt(action_result)
            except Exception as e:
                error_msg = self._get_error_message_from_exception(e)
                return action_result.set_status(phantom.APP_ERROR, f"Auth setup failed, expect downstream failure. Details: {error_msg}"), None
        else:
            return action_result.set_status(phantom.APP_ERROR, "No JWT or Refresh token found, expect downstream failure"), None

    def _request_new_jwt(self, action_result):
        config = self.get_config()
        headers = {
            "User-Agent": EXPANSE_USER_AGENT,
            "Authorization": f"Bearer {self._token}",
            "Content-Type": JSON_CONTENT_TYPE,
        }
        endpoint = f"{self._base_url}/api/v1/idtoken"
        r = requests.get(endpoint, headers=headers, verify=config.get("verify_server_cert", False), timeout=30)
        if r.status_code == STATUS_CODE_200:
            jwt = r.json().get("token")
            if jwt is not None:
                self._jwt = jwt
                self._state["jwt"] = jwt
                ret_val, decoded_jwt = self._decode_jwt(action_result, jwt)
                if phantom.is_fail(ret_val):
                    return action_result.get_status(), None
                self._state["jwt_exp"] = decoded_jwt["exp"]
                return phantom.APP_SUCCESS, jwt
            else:
                return action_result.set_status(phantom.APP_ERROR, "Invalid response returned from server when refreshing JWT"), None
        else:
            return action_result.set_status(phantom.APP_ERROR, "Invalid response returned from server when refreshing JWT"), None

    def _decode_jwt(self, action_result, token):
        # Uses based64 to decode a jwt to get expire timestamp
        parts = token.split(".")
        if len(parts) != 3:
            # Invalid JWT
            return action_result.set_status(phantom.APP_ERROR, "Invalid JWT token returned from server"), None
        # this is to avoid Incorrect padding TypeErrors in the base64 module
        padded_payload = f"{parts[1]}==="
        try:
            return phantom.APP_SUCCESS, json.loads(base64.b64decode(padded_payload.replace("-", "+").replace("_", "/")))
        except TypeError:
            return action_result.set_status(phantom.APP_ERROR, "Invalid JWT token returned from server"), None

    def _get_headers(self, jwt):
        return {"User-Agent": EXPANSE_USER_AGENT, "Content-Type": JSON_CONTENT_TYPE, "Authorization": f"JWT {jwt}"}

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        config = self.get_config()
        ret_val, jwt = self._fetch_jwt(action_result, config)
        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed")
            return action_result.get_status()

        self.save_progress("Connecting to endpoint")
        ret_val, response = self._make_rest_call("/api/v1/Entity/", action_result, params=None, headers=self._get_headers(jwt))

        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed")
            return action_result.get_status()

        # Return success
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_lookup_ip(self, param):
        config = self.get_config()

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))

        ret_val, jwt = self._fetch_jwt(action_result, config)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ip = param["ip"]

        ret_val, response = self._make_rest_call(
            "/api/v2/ip-range", action_result, params={"include": IP_LOOKUP_INCLUDE_PARAMS, "inet": ip}, headers=self._get_headers(jwt)
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        summary = action_result.update_summary({})
        summary["data"] = response.get("data")

        # Improve severity stats
        if len(response.get("data", [])) > 0:
            if len(response["data"][0].get("severityCounts", [])) > 0:
                sev_counts = {}
                for cts in response["data"][0].get("severityCounts", []):
                    sev_counts[cts["type"]] = cts.get("count")
                summary["data"][0]["severity_counts"] = sev_counts

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_lookup_domain(self, param):
        config = self.get_config()

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        ret_val, jwt = self._fetch_jwt(action_result, config)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        domain = param["domain"]

        ret_val, response = self._make_rest_call(
            "/api/v2/assets/domains", action_result, params={"domainSearch": domain}, headers=self._get_headers(jwt)
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        summary = action_result.update_summary({})
        summary["data"] = response.get("data")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_lookup_certificate(self, param):
        config = self.get_config()

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        ret_val, jwt = self._fetch_jwt(action_result, config)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        common_name = param["common_name"]

        ret_val, response = self._make_rest_call(
            "/api/v2/assets/certificates", action_result, params={"commonNameSearch": common_name}, headers=self._get_headers(jwt)
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        summary = action_result.update_summary({})
        summary["data"] = response.get("data")

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_lookup_behavior(self, param):
        config = self.get_config()

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")

        action_result = self.add_action_result(ActionResult(dict(param)))
        ret_val, jwt = self._fetch_jwt(action_result, config)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ip = param["ip"]

        start_date = datetime.strftime(datetime.today() - timedelta(days=30), "%Y-%m-%d")

        params = {"filter[created-after]": f"{start_date}T00:00:00.000Z", "filter[internal-ip-range]": ip, "page[limit]": 30}

        ret_val, response = self._make_rest_call("/api/v1/behavior/risky-flows", action_result, params=params, headers=self._get_headers(jwt))

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        summary = action_result.update_summary({})
        summary["data"] = response.get("data")

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        elif action_id == "lookup_ip":
            ret_val = self._handle_lookup_ip(param)

        elif action_id == "lookup_domain":
            ret_val = self._handle_lookup_domain(param)

        elif action_id == "lookup_certificate":
            ret_val = self._handle_lookup_certificate(param)

        elif action_id == "lookup_behavior":
            ret_val = self._handle_lookup_behavior(param)

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()
        if not isinstance(self._state, dict):
            self.debug_print("Resetting the state file with the default format")
            self._state = {"app_version": self.get_app_json().get("app_version")}
            return self.set_status(phantom.APP_ERROR, EXPANSE_STATE_FILE_CORRUPT_ERR)

        # Custom validator for IP address
        self.set_validator("ip", self._is_ip)

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse
    import sys

    import pudb

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")

    args = argparser.parse_args()
    session_id = None

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = ExpanseConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
