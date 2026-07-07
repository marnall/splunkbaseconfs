# File: zendesk_connector.py
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
"""Code that implements calls made to the zendesk systems device"""

# Phantom imports
import phantom.app as phantom
import requests
import simplejson as json
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# THIS Connector imports
import zendesk_consts as consts


class ZendeskConnector(BaseConnector):
    # actions supported by this script
    ACTION_ID_LIST_TICKETS = "list_tickets"
    ACTION_ID_CREATE_TICKET = "create_ticket"
    ACTION_ID_GET_TICKET = "get_ticket"
    ACTION_ID_UPDATE_TICKET = "update_ticket"
    ACTION_ID_RUN_QUERY = "run_query"

    def __init__(self):
        self.__id_to_name = {}
        self._base_url = None
        self._host = None
        self._headers = None
        self._api_uri = None
        self._key = None
        self._username = None
        self._auth_method = None

        # Call the BaseConnectors init first
        super().__init__()

    def initialize(self):
        """Called once for every action, all member initializations occur here"""

        config = self.get_config()

        # Get the Base URL from the asset config and so some cleanup
        self._base_url = config[consts.ZENDESK_JSON_DEVICE_URL].rstrip("/")

        # The host member extracts the host from the URL, is used in creating status messages
        self._host = self._base_url[self._base_url.find("//") + 2 :]

        # The headers, initialize them here once and use them for all other REST calls
        self._headers = {"Accept": "application/json"}

        # The common part after the base url, but before the specific endpoint
        # Initialized here and used on every REST endpoint calls
        self._api_uri = "/api/v2"

        password = config.get(phantom.APP_JSON_PASSWORD)
        api_token = config.get(consts.ZENDESK_JSON_API_TOKEN)

        if not (password or api_token):
            return self.set_status(phantom.APP_ERROR, "Please specify one of either 'Password' or 'API Token'")

        self._username = config[phantom.APP_JSON_USERNAME]

        self._auth_method = "password"

        if password:
            self._key = password
        else:
            self._key = api_token
            self._username += "/token"
            self._auth_method = "api token"

        return phantom.APP_SUCCESS

    def _make_rest_call(self, endpoint, action_result, headers=None, params=None, data=None, method="get"):
        """Function that makes the REST call to the device, generic function that can be called from various action
        handlers"""

        if headers is None:
            headers = {}

        # Create the headers
        headers.update(self._headers)

        if method in consts.ZENDESK_REQUEST_METHODS:
            headers.update({"Content-Type": "application/json"})

        resp_json = None

        # get or post or put, whatever the caller asked us to use, if not specified the default will be 'get'
        request_func = getattr(requests, method)

        # handle the error in case the caller specified a non-existent method
        if not request_func:
            action_result.set_status(phantom.APP_ERROR, consts.ZENDESK_ERR_API_UNSUPPORTED_METHOD, method=method)

        self.save_progress(f"Using {self._auth_method} for authentication")

        # Make the call
        try:
            r = request_func(
                self._base_url + self._api_uri + endpoint,  # The complete url is made up of the base_url, the api url and the endpiont
                auth=(self._username, self._key),  # The authentication method, currently set to simple base authentication
                data=json.dumps(data) if data else None,  # the data, converted to json string format if present, else just set to None
                headers=headers,  # The headers to send in the HTTP call
                verify=True,  # cert verification should be true
                params=params,
            )  # uri parameters if any
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, consts.ZENDESK_ERR_SERVER_CONNECTION, e), resp_json

        # self.debug_print('REST url: {0}'.format(r.url))

        # Try a json parse, since most REST API's give back the data in json.
        # If the device does not return JSONs, then need to implement parsing them some other manner.
        try:
            resp_json = r.json()
        except Exception as e:
            # r.text is guaranteed to be NON None, it will be empty, but not None
            try:
                msg_string = consts.ZENDESK_ERR_JSON_PARSE.format(raw_text=r.text.encode("utf-8"))
            except:
                msg_string = "Unable to parse response as a Json"
            if len(msg_string) > 500:
                msg_string = "Error while parsing the response"
            return action_result.set_status(phantom.APP_ERROR, msg_string, e), resp_json

        if r.status_code in consts.ZENDESK_EMPTY_RESPONSE_STATUS_CODES:
            return phantom.APP_SUCCESS, resp_json

        # Handle/process any errors that we get back from the device
        if 200 <= r.status_code <= 399:
            # Success
            return phantom.APP_SUCCESS, resp_json

        # Failure
        action_result.add_data(resp_json)

        details = json.dumps(resp_json).replace("{", "").replace("}", "")

        return action_result.set_status(
            phantom.APP_ERROR, consts.ZENDESK_ERR_FROM_SERVER.format(status=r.status_code, detail=details)
        ), resp_json

    def _test_connectivity(self, param):
        """Function that handles the test connectivity action, it is much simpler than other action handlers."""

        # Progress
        self.save_progress(consts.ZENDESK_USING_BASE_URL, base_url=self._base_url)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        # set the endpoint
        endpoint = "/tickets/recent.json"

        params = {"per_page": 1}

        # Action result to represent the call
        action_result = ActionResult()

        # Progress message, since it is test connectivity, it pays to be verbose
        self.save_progress(consts.ZENDESK_MSG_GET_INCIDENT_TEST)

        # Make the rest endpoint call
        ret_val, response = self._make_rest_call(endpoint, action_result, params=params)

        # Process errors
        if phantom.is_fail(ret_val):
            # Dump error messages in the log
            self.debug_print(action_result.get_message())

            # Set the status of the complete connector result
            self.set_status(phantom.APP_ERROR, action_result.get_message())

            # Append the message to display
            self.append_to_message(consts.ZENDESK_ERR_CONNECTIVITY_TEST)

            # return error
            return phantom.APP_ERROR

        # Set the status of the connector result
        return self.set_status_save_progress(phantom.APP_SUCCESS, consts.ZENDESK_SUCC_CONNECTIVITY_TEST)

    def _get_fields(self, param, action_result):
        """Validates the field parameter that is a json, created a function to make the caller code cleaner"""

        fields = param.get(consts.ZENDESK_JSON_FIELDS)

        # fields is an optional field
        if not fields:
            return phantom.APP_SUCCESS, None

        # we take in as a dictionary string, first try to load it as is
        try:
            fields = json.loads(fields)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, consts.ZENDESK_ERR_FIELDS_JSON_PARSE, e), None

        return phantom.APP_SUCCESS, fields

    def _add_names_to_ids(self, ticket):
        """Function parses the ticket and adds names to all the ids present in it"""

        user_id_keys = ["submitter_id", "assignee_id", "requester_id"]

        for user_id_key in user_id_keys:
            user_id = ticket[user_id_key]

            key_name = f"{user_id_key}_name"

            user_name = self.__id_to_name.get(user_id)

            if user_name:
                ticket[key_name] = user_name
                continue

            user_details_ar = ActionResult()

            endpoint = f"/users/{user_id}.json"

            # Make the rest call
            ret_val, response = self._make_rest_call(endpoint, user_details_ar)
            if phantom.is_fail(ret_val):
                continue

            user = response.get("user")
            if not user:
                continue

            ticket[key_name] = user.get("name")
            if ticket[key_name]:
                self.__id_to_name[user_id] = ticket[key_name]

        return

    def _create_ticket(self, param):
        """Action handler for the 'create ticket' action"""

        # This is an action that needs to be represented by the ActionResult object
        # So create one and add it to 'self' (i.e. add it to the BaseConnector)
        # When the action_result is created this way, the parameter is also passed.
        # Other things like the summary, data and status is set later on.
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Progress
        self.save_progress(consts.ZENDESK_USING_BASE_URL, base_url=self._base_url)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        # Set the endpoint
        endpoint = "/tickets.json"

        ticket = {"subject": param[consts.ZENDESK_JSON_SUBJECT], "comment": {"body": param[consts.ZENDESK_JSON_DESCRIPTION]}}

        # Parse and set the fields parameter, it is optional
        ret_val, fields = self._get_fields(param, action_result)

        # Process error
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # If 'fields' is specified, use it i.e. add it to the data that will be sent off
        # If 'fields' is not a proper json i.e. some normal string or integer, it will throw an exception
        try:
            if fields:
                if fields.get("custom_fields"):
                    if not isinstance(fields["custom_fields"], list):
                        return action_result.set_status(phantom.APP_ERROR, "Invalid value for custom_field")

                    ret_val, response = self._handle_custom_fields(action_result=action_result, custom_fields=fields["custom_fields"])

                    if phantom.is_fail(ret_val):
                        return action_result.get_status()

                    fields["custom_fields"] = response
                ticket.update(fields)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, consts.ZENDESK_ERR_FIELDS_JSON_PARSE, e)

        data = {"ticket": ticket}

        # Make the rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, data=data, method="post")

        # Process/parse the errors encountered while making the REST call.
        if phantom.is_fail(ret_val):
            self.debug_print(action_result.get_message())
            self.set_status(phantom.APP_ERROR, action_result.get_message())
            return phantom.APP_ERROR

        # parse the response from the REST call, this is very specific to the device being managed
        created_ticket = response["ticket"]

        # Set the summary in the action_result
        action_result.set_summary({consts.ZENDESK_JSON_NEW_TICKET_ID: created_ticket["id"]})

        self._add_names_to_ids(created_ticket)

        # set the data
        action_result.add_data(created_ticket)

        # set the status
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_custom_fields(self, action_result, custom_fields):
        """This function is used to handle the custom fields in fields parameter."""

        endpoint = "/ticket_fields.json"

        ret_val, response = self._make_rest_call(endpoint, action_result=action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status(), None

        response_list = []
        for custom_field_item in custom_fields:
            keys_list = list(custom_field_item.keys())
            values_list = list(custom_field_item.values())

            if not keys_list or len(keys_list) > 1:
                return action_result.set_status(phantom.APP_ERROR, "Invalid value for field custom_filed"), None

            key = keys_list[0]
            value = values_list[0]
            for item in response.get("ticket_fields", []):
                if item["raw_title"] == key:
                    response_list.append({"id": item["id"], "value": value})
                    break

        return phantom.APP_SUCCESS, response_list

    def _update_ticket(self, param):
        """Action handler for the 'update ticket' action"""

        # This is an action that needs to be represented by the ActionResult object
        # So create one and add it to 'self' (i.e. add it to the BaseConnector)
        # When the action_result is created this way, the parameter is also passed.
        # Other things like the summary, data and status is set later on.
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Progress
        self.save_progress(consts.ZENDESK_USING_BASE_URL, base_url=self._base_url)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        # set the endpoint
        endpoint = f"/tickets/{param[consts.ZENDESK_JSON_TICKET_ID]}.json"

        # Parse and set the fields parameter, it is required for this action
        ret_val, fields = self._get_fields(param, action_result)

        # Process error
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if not fields:
            return action_result.set_status(phantom.APP_ERROR, consts.ZENDESK_ERR_EMPTY_FIELDS)

        if fields.get("custom_fields"):
            if not isinstance(fields["custom_fields"], list):
                return action_result.set_status(phantom.APP_ERROR, "Invalid value for custom_field")

            ret_val, response = self._handle_custom_fields(action_result=action_result, custom_fields=fields["custom_fields"])

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            fields["custom_fields"] = response

        data = {"ticket": fields}

        # Make the REST CAll
        ret_val, response = self._make_rest_call(endpoint, action_result, data=data, method="put")

        # Process the error
        if phantom.is_fail(ret_val):
            self.debug_print(action_result.get_message())
            return action_result.get_status()

        # Get the result
        ticket = response.get("ticket")

        self._add_names_to_ids(ticket)

        # Set the summary
        action_result.set_summary({consts.ZENDESK_JSON_UPDATED_TICKET_ID: ticket["id"]})

        # Add the data
        action_result.add_data(ticket)

        # Set the status
        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_ticket(self, param):
        """Action handler for the 'get ticket' action"""

        # This is an action that needs to be represented by the ActionResult object
        # So create one and add it to 'self' (i.e. add it to the BaseConnector)
        # When the action_result is created this way, the parameter is also passed.
        # Other things like the summary, data and status is set later on.
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Progress
        self.save_progress(consts.ZENDESK_USING_BASE_URL, base_url=self._base_url)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        # set the endpoint
        endpoint = f"/tickets/{param[consts.ZENDESK_JSON_TICKET_ID]}.json"

        # Make the rest call
        ret_val, response = self._make_rest_call(endpoint, action_result)

        # Process the error
        if phantom.is_fail(ret_val):
            self.debug_print(action_result.get_message())
            self.set_status(phantom.APP_ERROR, action_result.get_message())
            return phantom.APP_ERROR

        if not response.get("ticket"):
            return action_result.set_status(phantom.APP_ERROR, status_message="No data found")

        # Process the return result
        ticket = response["ticket"]

        self._add_names_to_ids(ticket)

        # Set the summary
        action_result.set_summary({consts.ZENDESK_JSON_GOT_TICKET_ID: ticket["id"]})

        # Add the data
        action_result.add_data(ticket)

        # Set the status
        return action_result.set_status(phantom.APP_SUCCESS)

    def _list_tickets(self, param):
        """Action handler for the 'list tickets' action"""

        # This is an action that needs to be represented by the ActionResult object
        # So create one and add it to 'self' (i.e. add it to the BaseConnector)
        # When the action_result is created this way, the parameter is also passed.
        # Other things like the summary, data and status is set later on.
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Progress
        self.save_progress(consts.ZENDESK_USING_BASE_URL, base_url=self._base_url)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        # Endpoint
        endpoint = "/tickets.json"

        params = {
            "per_page": param.get(consts.ZENDESK_JSON_PER_PAGE, consts.DEFAULT_MAX_RESULTS),
            "page": param.get(consts.ZENDESK_JSON_PAGE, 1),
        }

        # Make the rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, params=params)

        # Process errors
        if phantom.is_fail(ret_val):
            self.debug_print(action_result.get_message())
            self.set_status(phantom.APP_ERROR, action_result.get_message())
            return phantom.APP_ERROR

        # Process successful response
        tickets = response["tickets"]

        # Set the summary
        action_result.set_summary({consts.ZENDESK_JSON_TOTAL_TICKETS: len(tickets)})

        # Add each ticket as a data
        for ticket in tickets:
            self._add_names_to_ids(ticket)
            action_result.add_data(ticket)

        # Set the Status
        return action_result.set_status(phantom.APP_SUCCESS)

    def _run_query(self, param):
        """Action handler for the 'run query' action"""

        # This is an action that needs to be represented by the ActionResult object
        # So create one and add it to 'self' (i.e. add it to the BaseConnector)
        # When the action_result is created this way, the parameter is also passed.
        # Other things like the summary, data and status is set later on.
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Progress
        self.save_progress(consts.ZENDESK_USING_BASE_URL, base_url=self._base_url)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        # Endpoint
        endpoint = "/search.json"

        query_type = "ticket"

        # Parameters, I don't think these need to be url encoded
        request_params = {"query": f"type:{query_type} {param[consts.ZENDESK_JSON_QUERY]}"}

        request_params.update(
            {"per_page": param.get(consts.ZENDESK_JSON_PER_PAGE, consts.DEFAULT_MAX_RESULTS), "page": param.get(consts.ZENDESK_JSON_PAGE, 1)}
        )

        # Make the rest call
        ret_val, response = self._make_rest_call(endpoint, action_result, params=request_params)

        # Process errors
        if phantom.is_fail(ret_val):
            self.debug_print(action_result.get_message())
            self.set_status(phantom.APP_ERROR, action_result.get_message())
            return phantom.APP_ERROR

        # Process successfully response
        tickets = response.get("results", [])

        # Set the summary
        action_result.set_summary({consts.ZENDESK_JSON_TOTAL_TICKETS: response.get("count"), consts.ZENDESK_JSON_RETURNED_TICKETS: len(tickets)})

        for ticket in tickets:
            self._add_names_to_ids(ticket)
            # Add as data to the action result
            action_result.add_data(ticket)

        # Set the Status
        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        """Function that handles all the actions"""

        # Get the action that we are supposed to carry out, set it in the connection result object
        action = self.get_action_identifier()

        # Initialize it to success
        ret_val = phantom.APP_SUCCESS

        # Bunch if..elif to process actions
        if action == self.ACTION_ID_CREATE_TICKET:
            ret_val = self._create_ticket(param)
        elif action == self.ACTION_ID_LIST_TICKETS:
            ret_val = self._list_tickets(param)
        elif action == self.ACTION_ID_GET_TICKET:
            ret_val = self._get_ticket(param)
        elif action == self.ACTION_ID_UPDATE_TICKET:
            ret_val = self._update_ticket(param)
        elif action == self.ACTION_ID_RUN_QUERY:
            ret_val = self._run_query(param)
        elif action == phantom.ACTION_ID_TEST_ASSET_CONNECTIVITY:
            ret_val = self._test_connectivity(param)

        return ret_val


if __name__ == "__main__":
    import argparse
    import sys

    import pudb

    pudb.set_trace()

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
            print("Accessing the Login page")
            r = requests.get(  # nosemgrep: python.requests.best-practice.use-timeout.use-timeout
                BaseConnector._get_phantom_base_url() + "login", verify=verify
            )
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = BaseConnector._get_phantom_base_url() + "login"

            print("Logging into Platform to get the session id")
            r2 = requests.post(  # nosemgrep: python.requests.best-practice.use-timeout.use-timeout
                BaseConnector._get_phantom_base_url() + "login", verify=verify, data=data, headers=headers
            )
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platfrom. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = ZendeskConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
