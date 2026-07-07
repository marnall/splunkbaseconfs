# File: metadefender_sandbox_connector.py
#
# Copyright (c) OPSWAT, 2024
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

import json
import time

# Phantom App imports
import phantom.app as phantom
import phantom.rules as ph_rules
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Usage of the consts file is recommended
from metadefender_sandbox_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class MetaDefenderSandboxConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super(MetaDefenderSandboxConnector, self).__init__()

        self._state = None
        self._server_url = None
        self._api_key = None
        self._headers = dict()
        self._poll_interval = 5
        self._timeout = 60

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(
                phantom.APP_ERROR, "Empty response and no information in the header"
            ),
            None,
        )

    def _process_html_response(self, response, action_result):
        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except:
            error_text = "Cannot parse error details"

        message = "Status Code: {0}. Data from server:\n{1}\n".format(
            status_code, error_text
        )

        message = message.replace("{", "{{").replace("}", "}}")
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    "Unable to parse JSON response. Error: {0}".format(str(e)),
                ),
                None,
            )

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {0} Data from server: {1}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        # Process each 'Content-Type' of response separately

        # Process a json response
        if "json" in r.headers.get("Content-Type", "") and r.status_code == 200:
            return self._process_json_response(r, action_result)

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if "html" in r.headers.get("Content-Type", "") and r.status_code == 200:
            return self._process_html_response(r, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text and r.status_code == 200:
            return self._process_empty_response(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {0} Data from server: {1}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), message)

    def _make_rest_call(self, endpoint, action_result, method="get", **kwargs):
        # **kwargs can be any additional parameters that requests.request accepts

        config = self.get_config()
        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR, "Invalid method: {0}".format(method)
                ),
                resp_json,
            )

        # Create a URL to connect to
        url = self._server_url + endpoint

        try:
            r = request_func(
                url,
                # auth=(username, password),  # basic authentication
                verify=config.get("verify_server_cert", False),
                timeout=self._timeout,
                **kwargs,
            )

        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    "Error Connecting to server. Details: {0}".format(str(e)),
                ),
                resp_json,
            )

        return self._process_response(r, action_result)

    def _poll_result(self, action_result, flow_id):
        elapsed_time = 0
        summary_data = action_result.update_summary({})
        filters = [
            "filter=general",
            "filter=finalVerdict",
            "filter=allTags",
            "filter=overallState",
            "filter=taskReference",
            "filter=subtaskReferences",
            "filter=allSignalGroups",
        ]

        filters_query = "&".join(filters)
        endpoint = METADEFENDER_SANDBOX_ENDPOINT_SCAN_POLL.format(
            id=flow_id, filters=filters_query
        )
        poll_count = 0
        response_status = None
        response_data = None
        try:
            while elapsed_time <= self._timeout:
                response_status, response_data = self._make_rest_call(
                    endpoint, action_result, headers=self._headers, method="get"
                )
                poll_count += 1
                self.save_progress("Polling attempt {0}".format(poll_count))

                if phantom.is_fail(response_status):
                    return response_status

                if response_data.get("allFinished", False):
                    self.save_progress("Polling finished.")
                    summary = {
                        "total_benign": 0,
                        "total_unknown": 0,
                        "total_no_threat": 0,
                        "total_suspicious": 0,
                        "total_likely_malicious": 0,
                        "total_malicious": 0,
                        "total_rejected": 0,
                        "rejected_reasons": [],
                        "flow_id": flow_id,
                    }

                    for report_id, report in response_data.get("reports", {}).items():
                        action_result.add_data(report)
                        verdict = (
                            report.get("finalVerdict", {})
                            .get("verdict", "unknown")
                            .lower()
                        )
                        if verdict == "informational":
                            verdict = "no_threat"
                        summary[f"total_{verdict}"] += 1

                    rejected = response_data.get("rejected_files", None)
                    if rejected:
                        summary["total_rejected"] = len(rejected)
                        summary["rejected_reasons"] = [
                            x.get("rejected_reason") for x in rejected
                        ]

                    summary_data.update(summary)
                    return action_result.set_status(phantom.APP_SUCCESS)
                if elapsed_time + self._poll_interval > self._timeout:
                    time.sleep(self._timeout - elapsed_time)
                    elapsed_time += self._timeout - elapsed_time
                else:
                    time.sleep(self._poll_interval)
                    elapsed_time += self._poll_interval

            return action_result.set_status(phantom.APP_SUCCESS)
        except Exception as e:
            return action_result.set_status(
                phantom.APP_ERROR, self._get_error_message_from_exception(e)
            )

    def _handle_test_connectivity(self, param):
        """This function is used to handle the test connectivity action"""

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Connecting to endpoint")

        ret_val, response = self._make_rest_call(
            METADEFENDER_SANDBOX_ENDPOINT_USERINFO,
            action_result,
            params=None,
            headers={"X-Api-Key": self._api_key},
        )

        if phantom.is_fail(ret_val):
            self.save_progress(action_result.get_message())
            self.save_progress("ERROR: Test Connectivity Failed.")
            return action_result.set_status(phantom.APP_ERROR)

        # Return success
        self.save_progress(
            f"Test Connectivity Passed. \n{response['username']} API key has been set successfully."
        )
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_detonate_url(self, param):
        """This function is used to submit a URL for analysis on MetaDefender Sandbox"""
        try:
            self.save_progress(
                "In action handler for: {0}".format(self.get_action_identifier())
            )
            action_result = self.add_action_result(ActionResult(dict(param)))
            data = {"url": param["url"]}

            if param.get("password", None):
                data["password"] = param.get("password", "")
            if param.get("is_private", None):
                data["is_private"] = param.get("is_private", "true")
            if param.get("description", None):
                data["description"] = param.get("description", "")

            response_status, response_data = self._make_rest_call(
                METADEFENDER_SANDBOX_ENDPOINT_SCAN_URL,
                action_result,
                method="post",
                data=data,
                headers=self._headers,
            )

            if not response_status:
                self.save_progress(f"ERROR: {response_data} | URL: {data}")
                return action_result.set_status(
                    phantom.APP_ERROR, f"ERROR: {response_data}"
                )

            flow_id = response_data.get("flow_id", None)
            if not flow_id:
                return action_result.set_status(
                    phantom.APP_ERROR, "ERROR: The flow_id to be polled is missing"
                )

            self.save_progress(f"Request flow_id: {flow_id}")
            return self._poll_result(action_result, flow_id)
        except Exception as e:
            self.save_progress(f"ERROR: Detonate URL failure: {e!r}")
            return action_result.set_status(
                phantom.APP_ERROR, f"ERROR: URL detonation failure: {e!r}"
            )

    def _handle_detonate_file(self, param):
        """This function is used to submit a file for analysis on MetaDefender Sandbox"""
        try:
            self.save_progress(
                "In action handler for: {0}".format(self.get_action_identifier())
            )
            action_result = self.add_action_result(ActionResult(dict(param)))

            vault_id = param.get("vault_id")
            if not vault_id:
                self.save_progress("The vault_id is missing")
                return action_result.set_status(
                    phantom.APP_ERROR, "The vault_id is missing"
                )

            _, _, file_info = ph_rules.vault_info(
                container_id=self.get_container_id(), vault_id=vault_id
            )
            if not file_info:
                self.save_progress("ERROR: Could not retrieve vault file")
                return action_result.set_status(
                    phantom.APP_ERROR, "ERROR: Could not retrieve vault file"
                )
            file_info = list(file_info)[0]
            file_path = file_info["path"]
            file_name = file_info["name"]
            files = [
                ("file", (file_name, open(file_path, "rb"), "application/octet-stream"))
            ]

            self.debug_print(f"Detonate file: {file_name}")

            data = {}
            if param.get("password", None):
                data["password"] = param.get("password", "")
            if param.get("is_private", None):
                data["is_private"] = param.get("is_private", "true")
            if param.get("description", None):
                data["description"] = param.get("description", "")

            response_status, response_data = self._make_rest_call(
                METADEFENDER_SANDBOX_ENDPOINT_SCAN_FILE,
                action_result,
                method="post",
                data=data,
                files=files,
                headers=self._headers,
            )

            if not response_status:
                self.save_progress(f"ERROR: {response_data}")
                return action_result.set_status(
                    phantom.APP_ERROR, f"ERROR: {response_data}"
                )

            flow_id = response_data.get("flow_id", None)
            if not flow_id:
                self.save_progress("ERROR: The flow_id to be polled is missing")
                return action_result.set_status(
                    phantom.APP_ERROR, "ERROR: The flow_id to be polled is missing"
                )

            self.save_progress(f"Request flow_id: {flow_id}")
            return self._poll_result(action_result, flow_id)
        except Exception as e:
            self.save_progress(f"Detonate file failure: {e!r}")
            return action_result.set_status(
                phantom.APP_ERROR, f"ERROR: File detonation failure: {e!r}"
            )

    def _handle_search_terms(self, param):
        """This function is used to search between MetaDefender Sandbox reports"""
        try:
            self.save_progress(
                "In action handler for: {0}".format(self.get_action_identifier())
            )
            action_result = self.add_action_result(ActionResult(dict(param)))
            summary_data = action_result.update_summary({})

            items = []
            query_string = param.get("query", "")
            page_size = param.get("page_size", None)
            page = param.get("page", None)
            limit = param.get("limit") or 10
            total_available_items = 0
            if (page_size and int(page_size) not in [5, 10, 20]) or \
                (page and int(page) <= 0) or \
                    (limit and (int(limit) <= 0 or int(limit) > 50)):
                self.save_progress("ERROR: Invalid parameter")
                return action_result.set_status(
                    phantom.APP_ERROR, "ERROR: Invalid parameter"
                )

            if page_size and not page:
                page = 1
            elif not page_size and page:
                page_size = 10
            if page_size and page:
                params = {
                    "query": query_string,
                    "page_size": int(page_size),
                    "page": int(page),
                }
                response_status, response_data = self._make_rest_call(
                    METADEFENDER_SANDBOX_ENDPOINT_SERACH,
                    action_result,
                    headers=self._headers,
                    method="get",
                    params=params,
                )
                if not response_status:
                    self.save_progress(f"ERROR: {response_data}")
                    return action_result.set_status(
                        phantom.APP_ERROR, f"ERROR: {response_data}"
                    )
                items = response_data.get("items", [])
                total_available_items = response_data.get("count", len(items))
            else:
                page_size = 20
                page = 1
                params = {"query": query_string, "page_size": page_size, "page": page}
                continue_query = True
                while continue_query:
                    response_status, response_data = self._make_rest_call(
                        METADEFENDER_SANDBOX_ENDPOINT_SERACH,
                        action_result,
                        headers=self._headers,
                        method="get",
                        params=params,
                    )
                    if not response_status:
                        self.save_progress(f"ERROR: {response_data}")
                        return action_result.set_status(
                            phantom.APP_ERROR, f"ERROR: {response_data}"
                        )
                    actual_items = response_data.get("items", [])
                    total_available_items = response_data.get("count", len(items))
                    items += actual_items
                    page += 1
                    # queried all or reached the limit
                    if total_available_items == len(items) or len(items) >= limit:
                        continue_query = False
                items = items[0:limit]

            summary = {
                "total_benign": 0,
                "total_unknown": 0,
                "total_no_threat": 0,
                "total_suspicious": 0,
                "total_likely_malicious": 0,
                "total_malicious": 0,
                "available_report_count": total_available_items,
            }
            if items:
                for item in items:
                    action_result.add_data(item)
                    verdict = item.get("verdict", "unknown").lower()
                    if verdict == "informational":
                        verdict = "no_threat"

                    summary[f"total_{verdict}"] += 1
                summary_data.update(summary)
                self.save_progress(f"{len(items)} results were found!")
            else:
                self.save_progress("No results were found!")
            return action_result.set_status(phantom.APP_SUCCESS)
        except Exception as e:
            self.save_progress(f"Search terms query failure: {e!r}")
            return action_result.set_status(
                phantom.APP_ERROR, f"ERROR: Search terms query failure: {e!r}"
            )

    def _handle_reputation(self, param, endpoint, request_params):
        """This function is used to get fast reputation about sha256, ip, domain or url"""
        try:
            action_result = self.add_action_result(ActionResult(dict(param)))
            summary_data = action_result.update_summary({})

            response_status, response_data = self._make_rest_call(
                endpoint,
                action_result,
                headers=self._headers,
                method="get",
                params=request_params,
            )
            if not response_status:
                self.save_progress(f"ERROR: {response_data}")
                return action_result.set_status(
                    phantom.APP_ERROR, f"ERROR: {response_data}"
                )

            self.save_progress(
                f"Reputation is {response_data.get('overall_verdict', 'unknown')}"
            )
            if response_data.get("filescan_reports"):
                response_data["filescan_reports"] = response_data["filescan_reports"][
                    :10
                ]
            action_result.add_data(response_data)
            summary_data.update(
                {
                    "verdict": response_data.get("overall_verdict", "unknown"),
                }
            )
            return action_result.set_status(phantom.APP_SUCCESS)
        except Exception as e:
            self.save_progress(f"Search terms query failure: {e!r}")
            return action_result.set_status(
                phantom.APP_ERROR, f"ERROR: Search terms query failure: {e!r}"
            )

    def _handle_file_reputation(self, param):
        try:
            self.save_progress(
                "In action handler for: {0}".format(self.get_action_identifier())
            )
            action_result = self.add_action_result(ActionResult(dict(param)))
            endpoint = f"{METADEFENDER_SANDBOX_ENDPOINT_REPUTATION}/hash"
            request_params = {"sha256": param.get("sha256", None)}
            self.debug_print(f"Endpoint call: {endpoint}")
            return self._handle_reputation(param, endpoint, request_params)
        except Exception as e:
            self.save_progress(f"File reputation error: {e!r}")
            return action_result.set_status(
                phantom.APP_ERROR, f"ERROR: File reputation error: {e!r}"
            )

    def _handle_ip_reputation(self, param):
        try:
            self.save_progress(
                "In action handler for: {0}".format(self.get_action_identifier())
            )
            action_result = self.add_action_result(ActionResult(dict(param)))
            endpoint = f"{METADEFENDER_SANDBOX_ENDPOINT_REPUTATION}/ip"
            request_params = {"ioc_value": param.get("ip")}
            self.debug_print(f"Endpoint call: {endpoint}")
            return self._handle_reputation(param, endpoint, request_params)
        except Exception as e:
            self.save_progress(f"IP reputation error: {e!r}")
            return action_result.set_status(
                phantom.APP_ERROR, f"ERROR: IP reputation error: {e!r}"
            )

    def _handle_domain_reputation(self, param):
        try:
            self.save_progress(
                "In action handler for: {0}".format(self.get_action_identifier())
            )
            action_result = self.add_action_result(ActionResult(dict(param)))
            endpoint = f"{METADEFENDER_SANDBOX_ENDPOINT_REPUTATION}/domain"
            request_params = {"ioc_value": param.get("domain")}
            self.debug_print(f"Endpoint call: {endpoint}")
            return self._handle_reputation(param, endpoint, request_params)
        except Exception as e:
            self.save_progress(f"Domain reputation error: {e!r}")
            return action_result.set_status(
                phantom.APP_ERROR, f"ERROR: Domain reputation error: {e!r}"
            )

    def _handle_url_reputation(self, param):
        try:
            self.save_progress(
                "In action handler for: {0}".format(self.get_action_identifier())
            )
            action_result = self.add_action_result(ActionResult(dict(param)))
            endpoint = f"{METADEFENDER_SANDBOX_ENDPOINT_REPUTATION}/url"
            request_params = {"ioc_value": param.get("url")}
            self.debug_print(f"Endpoint call: {endpoint}")
            return self._handle_reputation(param, endpoint, request_params)
        except Exception as e:
            self.save_progress(f"URL reputation error: {e!r}")
            return action_result.set_status(
                phantom.APP_ERROR, f"ERROR: URL reputation error: {e!r}"
            )

    def handle_action(self, param):
        action_list = {
            "test_connectivity": self._handle_test_connectivity,
            "detonate_url": self._handle_detonate_url,
            "detonate_file": self._handle_detonate_file,
            "search_terms": self._handle_search_terms,
            "file_reputation": self._handle_file_reputation,
            "ip_reputation": self._handle_ip_reputation,
            "domain_reputation": self._handle_domain_reputation,
            "url_reputation": self._handle_url_reputation,
        }

        # Get the action that we are supposed to execute for this App Run
        action = self.get_action_identifier()
        ret_val = phantom.APP_SUCCESS

        self.debug_print(f"action: {self.get_action_identifier()}")

        if action in list(action_list.keys()):
            function = action_list[action]
            ret_val = function(param)

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()
        """
        # Access values in asset config by the name

        # Required values can be accessed directly
        required_config_name = config['required_config_name']

        # Optional values should use the .get() function
        optional_config_name = config.get('optional_config_name')
        """

        self._server_url = config.get("server_url")
        self._api_key = config.get("api_key")
        self._headers = {"X-Api-Key": self._api_key}
        self._poll_interval = int(config.get("poll_interval"))
        self._timeout = int(config.get("timeout"))

        if (
            self._timeout < METADEFENDER_SANDBOX_TIMEOUT_MIN or self._timeout > METADEFENDER_SANDBOX_TIMEOUT_MAX
        ):
            self.save_progress(
                f"ERROR: Detonate timeout must be an integer between {METADEFENDER_SANDBOX_TIMEOUT_MIN} and {METADEFENDER_SANDBOX_TIMEOUT_MAX}!"
            )
            return phantom.APP_ERROR
        if (
            self._poll_interval < METADEFENDER_SANDBOX_POLL_INTERVAL_MIN or self._poll_interval > METADEFENDER_SANDBOX_POLL_INTERVAL_MAX
        ):
            self.save_progress(
                "ERROR: Poll interval must be an integer between"
                f"{METADEFENDER_SANDBOX_POLL_INTERVAL_MIN} and {METADEFENDER_SANDBOX_POLL_INTERVAL_MAX}!"
            )
            return phantom.APP_ERROR

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse
    import sys

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)
    argparser.add_argument("-v", "--verify", action="store_true", help="verify", required=False, default=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password
    verify = args.verify

    if username is not None and password is None:

        # User specified a username but not a password, so ask
        import getpass

        password = getpass.getpass("Password: ")

    if username and password:
        try:
            login_url = MetaDefenderSandboxConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = MetaDefenderSandboxConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
