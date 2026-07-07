# File: brinqa_connector.py
#
# Copyright (c) Asurion, 2023-2025
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

# Phantom App imports
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class BrinqaConnector(BaseConnector):
    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"),
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

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"

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
                    f"Unable to parse JSON response. Error: {e!s}",
                ),
                None,
            )

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            if resp_json:
                if resp_json.get("errors"):
                    return RetVal(
                        action_result.set_status(
                            phantom.APP_ERROR,
                            status_message=resp_json.get("errors")[0].get("message"),
                        ),
                        resp_json,
                    )
                message = "Graph query successful"
                return RetVal(action_result.set_status(phantom.APP_SUCCESS, message), resp_json)
            else:
                message = "Graph query returned, but contained no data."
                return RetVal(action_result.set_status(phantom.APP_SUCCESS, message))
            # Add if to check if empty

        # You should process the error returned in the json
        message = "Error from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )  # add clarification on error

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        # Process each 'Content-Type' of response separately
        self.debug_print(r.headers.get("Content-Type", ""))
        # Process a json response
        if "json" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result)

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if "html" in r.headers.get("Content-Type", ""):
            return self._process_html_response(r, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text:
            return self._process_empty_response(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, method="get", **kwargs):
        # **kwargs can be any additional parameters that requests.request accepts
        # **kwargs will be the JSON to make the query and any additional arguments.
        config = self.get_config()

        self.debug_print(self.get_config())

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"),
                resp_json,
            )

        # Create a URL to connect to
        url = "https://" + self._base_url + endpoint  # Accurate

        try:
            r = request_func(
                url,
                # auth=(username, password),  # basic authentication
                verify=config.get("verify_server_cert", False),
                **kwargs,
            )
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Error Connecting to server. Details: {e!s}",
                ),
                resp_json,
            )

        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # NOTE: test connectivity does _NOT_ take any parameters
        # i.e. the param dictionary passed to this handler will be empty.
        # Also typically it does not add any data into an action_result either.
        # The status and progress messages are more important.

        self.debug_print("Logging in")
        self._make_rest_call(f"/api/auth/authMethod?email={self._username}", action_result, method="get")
        # make rest call
        auth_post_body = {"username": self._username, "password": self._password}
        ret_val, response = self._make_rest_call("/api/auth/login", action_result, json=auth_post_body, method="post")
        # Accurate User, Pass, and Path here
        if phantom.is_fail(ret_val):
            self.debug_print("Failed to Logon.")
            return action_result.get_status()
        else:
            token = response["access_token"]
            token_type = response["token_type"]

        self.debug_print("Connecting to endpoint")
        # make rest call
        headers = {"Authorization": token_type + " " + token}
        user_post_body = {"query": "query confirmGraphqlAccessible {assets(limit: 1) {display}}"}
        ret_val, response = self._make_rest_call(
            "/graphql/tvm",
            action_result,
            headers=headers,
            json=user_post_body,
            method="post",
        )
        if phantom.is_fail(ret_val):
            self.debug_print("Test Connectivity Failed: Graph Response")
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    status_message="Test Connectivity Failed: Graph Response. Check to make sure the credentials are correct.",
                ),
                None,
            )
        else:
            if response["data"]["assets"]:
                self.debug_print("Test Connectivity Passed")
                return RetVal(
                    action_result.set_status(
                        phantom.APP_SUCCESS,
                        status_message="Test Connectivity Passed",
                    ),
                    None,
                )
            else:
                self.debug_print("Test Connectivity Failed: Data. Check to make sure the account has GraphQL Permissions.")
                return RetVal(
                    action_result.set_status(
                        phantom.APP_ERROR,
                        status_message="Test Connectivity Failed: Data. Check to make sure the account has GraphQL Permissions.",
                    ),
                    None,
                )

    def _handle_query_brinqa(self, param) -> str:
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.debug_print("Logging in")
        self._make_rest_call(f"/api/auth/authMethod?email={self._username}", action_result, method="get")
        # make an auth rest call to login to Brinqa
        auth_post_body = {"username": self._username, "password": self._password}
        ret_val, response = self._make_rest_call("/api/auth/login", action_result, json=auth_post_body, method="post")
        if phantom.is_fail(ret_val):
            self.debug_print("Failed login.")
            return action_result.get_status()
        else:
            token = response["access_token"]
            token_type = response["token_type"]

        self.debug_print("Connecting to endpoint")
        # make a graph rest call to receive information about all items in identifier
        headers = {"Authorization": token_type + " " + token}
        if "filter" in param and "return_values" in param:
            data_model = f"{param['data_model']}"
            data_model_lower = data_model[0].lower() + data_model[1:]
            filter_string = f"{param['filter']}"
            return_string = f"{{{param['return_values']}}}"
            user_post_body = {
                "query": f'query MyQuery{{ {data_model_lower}(filter: "{filter_string}") {return_string}}}',
                "operationName": "MyQuery",
            }
        else:
            dataModelCap = f"{param['data_model']}".capitalize()
            user_post_body = {
                "query": f'query MyQuery{{ __type(name: "{dataModelCap}"){{fields{{name}}}}}}',
                "operationName": "MyQuery",
            }
        ret_val, response = self._make_rest_call(
            "/graphql/tvm",
            action_result,
            headers=headers,
            json=user_post_body,
            method="post",
        )

        self.debug_print(response.get("data"))
        try:
            for attribute in response.get("data", {}).get("__type", {}).get("fields", {}):
                action_result.add_data(attribute.get("name"))
        except AttributeError:
            pass
        if phantom.is_fail(ret_val):
            self.debug_print("Failed to return the graph query.")
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    status_message=response.get("errors")[0].get("message"),
                ),
                None,
            )
        else:
            if response.get("data", {}).get(f"{param['data_model']}") or response.get("data", False).get("__type"):
                if response.get("data", {}).get(f"{param['data_model']}"):
                    self.debug_print(response.get("data", {}).get(f"{param['data_model']}"))
                    action_result.add_data(response.get("data", {}).get(f"{param['data_model']}"))
                else:
                    self.debug_print(response.get("data", {}).get("__type"))
                return RetVal(
                    action_result.set_status(phantom.APP_SUCCESS, status_message="Graph query successful."),
                    None,
                )
            else:
                self.debug_print("Graph query returned, but contained no data.")
                return RetVal(
                    action_result.set_status(
                        phantom.APP_SUCCESS,
                        status_message="Graph query returned, but contained no data.",
                    ),
                    None,
                )

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)
        if action_id == "query_brinqa":
            ret_val = self._handle_query_brinqa(param)

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

        self._base_url = config.get("base_url")
        self._username = config.get("username")
        self._password = config.get("password")

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password

    if username is not None and password is None:
        # User specified a username but not a password, so ask

        import getpass

        password = getpass.getpass("Password: ")

    if username and password:
        try:
            login_url = "Http://" + BrinqaConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=False)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=False, data=data, headers=headers)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = BrinqaConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    exit(0)


if __name__ == "__main__":
    main()
