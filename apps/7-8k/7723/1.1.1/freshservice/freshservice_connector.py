# File: freshservice_connector.py

# Copyright (c) Orro Group, 2023

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.


# Python 3 Compatibility imports
from __future__ import print_function, unicode_literals

import json

# Phantom App imports
import phantom.app as phantom

# Usage of the consts file is recommended
# from freshservice_consts import *
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector


class RetVal(tuple):

    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class FreshServiceConnector(BaseConnector):

    def __init__(self):

        # Call the BaseConnectors init first
        super(FreshServiceConnector, self).__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"), None)

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

        message = "Status Code: {0}. Data from server:\n{1}\n".format(status_code, error_text)

        message = message.replace("{", "{{").replace("}", "}}")
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Unable to parse JSON response. Error: {0}".format(str(e))), None)

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {0} Data from server: {1}".format(r.status_code, r.text.replace("{", "{{").replace("}", "}}"))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        # Process each 'Content-Type' of response separately

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
        message = "Can't process response from server. Status Code: {0} Data from server: {1}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, method="get", **kwargs):
        # **kwargs can be any additional parameters that requests.request accepts

        config = self.get_config()

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Invalid method: {0}".format(method)), resp_json)

        # Create a URL to connect to
        url = self._base_url + endpoint

        try:
            r = request_func(
                url,
                # auth=(username, password),  # basic authentication
                verify=config.get("verify_server_cert", False),
                **kwargs,
            )
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Error Connecting to server. Details: {0}".format(str(e))), resp_json)

        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # NOTE: test connectivity does _NOT_ take any parameters
        # i.e. the param dictionary passed to this handler will be empty.
        # Also typically it does not add any data into an action_result either.
        # The status and progress messages are more important.

        self.save_progress("Connecting to endpoint")
        # make rest call
        ret_val, response = self._make_rest_call("riot-orro-test.freshservice.com", action_result, params=None, headers=None)

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress("Test Connectivity Failed.")
            # return action_result.get_status()

        # Return success
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

        # For now return Error with a message, in case of success we don't set the message, but use the summary
        return action_result.set_status(phantom.APP_ERROR, "Action not yet implemented")

    def _handle_create_ticket(self, param):
        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Set or get params
        subject = param.get("subject", "")
        description = param.get("description", "")
        requester_id = param.get("requester_id", "")
        priority = param.get("priority", "")
        status = param.get("status", "")
        group_id = param.get("group_id", "")
        custom_field = param.get("custom_field", "")
        custom_field_value = param.get("custom_field_value", "")
        # Create ticket endpoint, for this action.
        ct_endpoint = "/api/v2/tickets"
        # Import this module for the HTTPBasicAuth shortcut in the request rather than b64 encoding and authorization header.
        import requests
        from requests.auth import HTTPBasicAuth

        # HTTP POST
        url = "https://" + self._base_url + ct_endpoint
        if not custom_field == "":
            payload = {
                "subject": subject,
                "description": description,
                "requester_id": int(requester_id),
                "priority": int(priority),
                "status": int(status),
                "group_id": int(group_id),
                "custom_fields": {custom_field: custom_field_value},
            }
        else:
            payload = {
                "subject": subject,
                "description": description,
                "requester_id": int(requester_id),
                "priority": int(priority),
                "status": int(status),
                "group_id": int(group_id),
            }

        response = requests.request("POST", url, auth=HTTPBasicAuth(self._api_key, ":X"), json=payload)

        # Now post process the data,  uncomment code as you deem fit.
        # Add the response into the data section, after testing response as an invalid ticket gives no
        action_result.add_data(response.json())

        # Add a dictionary that is made up of the most important values from data into the summary
        # summary = action_result.update_summary({})
        # summary['ticket_id'] = (response.json()['ticket']['id'])
        # summary['summ'] = "Ticket created with ID " + str((response.json()['ticket']['id']))

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        if "ticket" in response.json():
            success_message = "Ticket created with ID " + str((response.json()["ticket"]["id"]))
            self.save_progress(success_message)
            return action_result.set_status(phantom.APP_SUCCESS, success_message)
        else:
            # For now return Error with a message, in case of success we don't set the message, but use the summary
            return action_result.set_status(phantom.APP_ERROR, "Ticket could not be created, check response data.")

    def _handle_get_ticket(self, param):
        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary

        # Set or get params
        ticket_id = param["ticket_id"]
        # Get ticket endpoint, for this action.
        gt_endpoint = "/api/v2/tickets/"
        # Import this module for the HTTPBasicAuth shortcut in the request rather than b64 encoding and authorization header.
        import requests
        from requests.auth import HTTPBasicAuth

        # HTTP POST
        url = "https://" + self._base_url + gt_endpoint + ticket_id
        response = requests.request("GET", url, auth=HTTPBasicAuth(self._api_key, ":X"))

        # Now post process the data,  uncomment code as you deem fit
        # Add the response into the data section
        if not ("404" in str(response)):
            action_result.add_data(response.json())
        else:
            response_str = """{"http_response": "404"}"""
            response_json = json.loads(response_str)
            action_result.add_data(response_json)

        # Add a dictionary that is made up of the most important values from data into the summary
        # summary = action_result.update_summary({})
        # summary['summ'] = "Got ticket ID " + str((response.json()['ticket']['id']))

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        if not ("404" in str(response)):
            success_message = "Got ticket ID " + str((response.json()["ticket"]["id"]))
            self.save_progress("Successfully fetched ticket information")
            return action_result.set_status(phantom.APP_SUCCESS, success_message)
        else:
            # For now return Error with a message, in case of success we don't set the message, but use the summary
            return action_result.set_status(phantom.APP_ERROR, "Ticket ID not found.")

    def _handle_add_note(self, param):
        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary

        # Required values can be accessed directly
        ticket_id = param["ticket_id"]
        body = param["body"]

        # Optional values should use the .get() function
        private = param.get("private", "")

        # Add note endpoint, for this action.
        an_endpoint = "/api/v2/tickets/"
        # Import this module for the HTTPBasicAuth shortcut in the request rather than b64 encoding and authorization header.
        import requests
        from requests.auth import HTTPBasicAuth

        # HTTP POST
        url_end = str(ticket_id) + "/notes"
        url = "https://" + self._base_url + an_endpoint + url_end
        if not private == "":
            payload = {"body": body}
        else:
            payload = {"body": body, "private": bool(False)}

        response = requests.request("POST", url, auth=HTTPBasicAuth(self._api_key, ":X"), json=payload)

        # Now post process the data,  uncomment code as you deem fit.
        # Add the response into the data section, after testing response as an invalid ticket gives no
        action_result.add_data(response.json())

        # Add a dictionary that is made up of the most important values from data into the summary
        # summary = action_result.update_summary({})
        # summary['ticket_id'] = (response.json()['ticket']['id'])
        # summary['summ'] = "Ticket created with ID " + str((response.json()['ticket']['id']))

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        if "conversation" in response.json():
            success_message = "Note created with conversation ID " + str((response.json()["conversation"]["id"]))
            self.save_progress(success_message)
            return action_result.set_status(phantom.APP_SUCCESS, success_message)
        else:
            # For now return Error with a message, in case of success we don't set the message, but use the summary
            return action_result.set_status(phantom.APP_ERROR, "Ticket could not be created, check response data.")

    def _handle_update_ticket(self, param):
        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary
        # Set or get params
        # Required values can be accessed directly
        ticket_id = param["ticket_id"]
        # Optional values should use the .get() function
        update_status = param.get("update_status", "")
        update_priority = param.get("update_priority", "")
        update_custom_field = param.get("update_custom_field", "")
        update_custom_field_value = param.get("update_custom_field_value", "")
        bypass_mandatory = param.get("bypass_mandatory", "")
        responder_id = param.get("responder_id", "")
        category = param.get("category", "")
        sub_category = param.get("sub_category", "")
        item_category = param.get("item_category", "")
        # Update ticket, endpoint for this action.
        update_endpoint = "/api/v2/tickets/"
        # Import this module for the HTTPBasicAuth shortcut in the request rather than b64 encoding and authorization header.
        import requests
        from requests.auth import HTTPBasicAuth

        # HTTP PUT
        # Create the payload depending on which optional fields were populated.
        # Assumes that the user entered the custom field value if they entered a custom field.
        # Also expect responder_id, category, sub_category and item_category to all be set as one action.
        # assigned_team became a new custom field as part of an new add-on that needs to be set at Resolved status too.
        if not update_priority == "":
            if not update_custom_field == "":
                if not responder_id == "":
                    payload = {
                        "priority": int(update_priority),
                        "status": int(update_status),
                        "custom_fields": {update_custom_field: update_custom_field_value, "assigned_team": "Security"},
                        "responder_id": int(responder_id),
                        "category": category,
                        "sub_category": sub_category,
                        "item_category": item_category,
                    }
                else:
                    payload = {
                        "priority": int(update_priority),
                        "status": int(update_status),
                        "custom_fields": {update_custom_field: update_custom_field_value},
                    }
            elif not responder_id == "":
                payload = {
                    "priority": int(update_priority),
                    "status": int(update_status),
                    "custom_fields": {"assigned_team": "Security"},
                    "responder_id": int(responder_id),
                    "category": category,
                    "sub_category": sub_category,
                    "item_category": item_category,
                }
            else:
                payload = {"priority": int(update_priority), "status": int(update_status)}
        elif not update_custom_field == "":
            if not responder_id == "":
                payload = {
                    "status": int(update_status),
                    "custom_fields": {update_custom_field: update_custom_field_value, "assigned_team": "Security"},
                    "responder_id": int(responder_id),
                    "category": category,
                    "sub_category": sub_category,
                    "item_category": item_category,
                }
            else:
                payload = {"status": int(update_status), "custom_fields": {update_custom_field: update_custom_field_value}}
        elif not responder_id == "":
            payload = {
                "status": int(update_status),
                "custom_fields": {"assigned_team": "Security"},
                "responder_id": int(responder_id),
                "category": category,
                "sub_category": sub_category,
                "item_category": item_category,
            }
        else:
            payload = {"status": int(update_status)}

        # Create the URL depending on bypass_mandatory being true or not.
        if not bypass_mandatory == "":
            url = "https://" + self._base_url + update_endpoint + ticket_id + "?bypass_mandatory=true"
        else:
            url = "https://" + self._base_url + update_endpoint + ticket_id

        response = requests.request("PUT", url, auth=HTTPBasicAuth(self._api_key, ":X"), json=payload)

        # Now post process the data,  uncomment code as you deem fit

        # Add the response into the data section
        action_result.add_data(response.json())

        # Add a dictionary that is made up of the most important values from data into the summary
        # summary = action_result.update_summary({})
        # summary['num_data'] = len(action_result['data'])

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        if "ticket" in response.json():
            self.save_progress("Successfully updated ticket")
            return action_result.set_status(phantom.APP_SUCCESS, "Ticket was updated.")
        else:
            # For now return Error with a message, in case of success we don't set the message, but use the summary
            return action_result.set_status(phantom.APP_ERROR, "Ticket could not be updated, check response data.")

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "create_ticket":
            ret_val = self._handle_create_ticket(param)

        if action_id == "get_ticket":
            ret_val = self._handle_get_ticket(param)

        if action_id == "add_note":
            ret_val = self._handle_add_note(param)

        if action_id == "update_ticket":
            ret_val = self._handle_update_ticket(param)

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

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
        self._api_key = config.get("api_key")

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
            login_url = FreshServiceConnector._get_phantom_base_url() + "/login"

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

        connector = FreshServiceConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
