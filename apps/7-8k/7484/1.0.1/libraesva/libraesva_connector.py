# File: libraesva_connector.py

# Copyright (c) Splunk, 2024

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
import pathlib
import urllib.parse as urlparse

import encryption_helper
# Phantom App imports
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from libraesva_consts import *


def _is_valid_asset_id(asset_id):
    """ This function validates an asset id.
    Must be an alphanumeric string of less than 128 characters.

    :param asset_id: asset_id
    :return: is_valid: Boolean True if valid, False if not.
    """
    if not isinstance(asset_id, str):
        return False
    if not asset_id.isalnum():
        return False
    if len(asset_id) > 128:
        return False
    return True


def _get_file_path(asset_id, is_state_file=True):
    """ This function gets the path of the auth status file of an asset id.

    :param asset_id: asset_id
    :param app_connector: Object of app_connector class
    :param is_state_file: boolean parameter for state file
    :return: file_path: Path object of the file
    """
    current_file_path = pathlib.Path(__file__).resolve()
    if is_state_file:
        input_file = f'{asset_id}_state.json'
    else:
        input_file = f'{asset_id}_oauth_task.out'
    output_file_path = current_file_path.with_name(input_file)
    return output_file_path


def _decrypt_state(state, salt):
    """
    Decrypts the state.
    :param state: state dictionary
    :param salt: salt used for decryption
    :return: decrypted state
    """

    if not state.get("is_encrypted"):
        return state

    access_token = state.get("token", {})
    if access_token:
        state["token"] = encryption_helper.decrypt(access_token, salt)

    return state


def _encrypt_state(state, salt):
    """
    Encrypts the state.
    :param state: state dictionary
    :param salt: salt used for encryption
    :return: encrypted state
    """

    access_token = state.get("token", {})
    if access_token:
        state["token"] = encryption_helper.encrypt(access_token, salt)

    state["is_encrypted"] = True

    return state


def _load_app_state(asset_id, app_connector=None):
    """ This function is used to load the current state file.

    :param asset_id: asset_id
    :param app_connector: Object of app_connector class
    :return: state: Current state file as a dictionary
    """

    asset_id = str(asset_id)
    if not _is_valid_asset_id(asset_id):
        if app_connector:
            app_connector.debug_print('In _load_app_state: Invalid asset_id')
        return {}

    state_file_path = _get_file_path(asset_id)

    state = {}
    try:
        with open(state_file_path, 'r') as state_file:
            state = json.load(state_file)
    except Exception as e:
        if app_connector:
            app_connector.error_print(f'In _load_app_state: Exception: {str(e)}')

    if app_connector:
        app_connector.debug_print('Loaded state: ', state)

    try:
        state = _decrypt_state(state, asset_id)
    except Exception as e:
        if app_connector:
            app_connector.error_print("{}: {}".format("Error decrypting the state file: ", str(e)))
        state = {}

    return state


def _save_app_state(state, asset_id, app_connector):
    """ This function is used to save current state in file.

    :param state: Dictionary which contains data to write in state file
    :param asset_id: asset_id
    :param app_connector: Object of app_connector class
    :return: status: phantom.APP_SUCCESS
    """
    asset_id = str(asset_id)
    if not _is_valid_asset_id(asset_id):
        if app_connector:
            app_connector.debug_print('In _save_app_state: Invalid asset_id')
        return {}

    state_file_path = _get_file_path(asset_id)

    try:
        state = _encrypt_state(state, asset_id)
    except Exception as e:
        if app_connector:
            app_connector.error_print("{}: {}".format("Error encrypting the state file: ", str(e)))
        return phantom.APP_ERROR

    if app_connector:
        app_connector.debug_print('Saving state: ', state)

    try:
        with open(state_file_path, 'w+') as state_file:
            json.dump(state, state_file)
    except Exception as e:
        if app_connector:
            app_connector.error_print(f'Unable to save state file: {str(e)}')

    return phantom.APP_SUCCESS


class RetVal(tuple):

    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class LibraesvaConnector(BaseConnector):

    def __init__(self):

        # Call the BaseConnectors init first
        super(LibraesvaConnector, self).__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None
        self._username = None
        self._password = None
        self._admin_user = None
        self._access_token = None

    def load_state(self):
        """
        Load the contents of the state file to the state dictionary and decrypt it.
        :return: loaded state
        """
        state = super().load_state()
        if not isinstance(state, dict):
            self.debug_print("Reseting the state file with the default format")
            state = {
                "app_version": self.get_app_json().get('app_version')
            }
            return state
        try:
            state = _decrypt_state(state, self.get_asset_id())
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            self.error_print("{}: {}".format("Error decrypting the state file: ", error_message))
            self.debug_print("Reseting the state file with the default format")
            state = {
                "app_version": self.get_app_json().get('app_version')
            }

        return state

    def save_state(self, state):
        """
        Encrypt and save the current state dictionary to the the state file.
        :param state: state dictionary
        :return: status
        """
        try:
            state = _encrypt_state(state, self.get_asset_id())
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            self.error_print("{}: {}".format("Error encrypting the state file: ", error_message))

        return super().save_state(state)

    def _dump_error_log(self, error, message="Exception occurred."):
        self.error_print(message, dump_object=error)

    def _get_error_message_from_exception(self, e):
        """
        Get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """
        error_code = None
        error_message = "Unknown error occurred. "

        self._dump_error_log(e)

        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_message = e.args[1]
                elif len(e.args) == 1:
                    error_message = e.args[0]
        except Exception:
            self.error_print("Exception occurred while getting error code and message")

        if not error_code:
            error_text = "Error Message: {}".format(error_message)
        else:
            error_text = "Error Code: {}. Error Message: {}".format(error_code, error_message)

        return error_text

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(
                phantom.APP_ERROR, "Empty response and no information in the header"
            ), None
        )

    def _process_html_response(self, response, action_result):
        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split('\n')
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = '\n'.join(split_lines)
        except:
            error_text = "Cannot parse error details"

        message = "Status Code: {0}. Data from server:\n{1}\n".format(status_code, error_text)

        message = message.replace(u'{', '{{').replace(u'}', '}}')
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR, "Unable to parse JSON response. Error: {0}".format(str(e))
                ), None
            )

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {0} Data from server: {1}".format(
            r.status_code,
            r.text.replace(u'{', '{{').replace(u'}', '}}')
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, 'add_debug_data'):
            action_result.add_debug_data({'r_status_code': r.status_code})
            action_result.add_debug_data({'r_text': r.text})
            action_result.add_debug_data({'r_headers': r.headers})

        # Process each 'Content-Type' of response separately

        # Process a json response
        if 'json' in r.headers.get('Content-Type', ''):
            return self._process_json_response(r, action_result)

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if 'html' in r.headers.get('Content-Type', ''):
            return self._process_html_response(r, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text:
            return self._process_empty_response(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {0} Data from server: {1}".format(
            r.status_code,
            r.text.replace('{', '{{').replace('}', '}}')
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, verify=True, headers=None, params=None, data=None, json=None, method="get"):
        """ Function that makes the REST call to the app.

        :param endpoint: REST endpoint that needs to appended to the service address
        :param action_result: object of ActionResult class
        :param headers: request headers
        :param params: request parameters
        :param data: request body
        :param json: JSON object
        :param method: GET/POST/PUT/DELETE/PATCH (Default will be GET)
        :param verify: verify server certificate (Default True)
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        response obtained by making an API call
        """

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), resp_json)

        try:
            resp_json = request_func(endpoint, json=json, data=data, headers=headers, verify=verify, params=params, timeout=30)
        except Exception as e:
            error_message = f"Error connecting to server. Details: {self._get_error_message_from_exception(e)}"
            return RetVal(action_result.set_status(phantom.APP_ERROR, error_message), resp_json)

        return self._process_response(resp_json, action_result)

    def _make_rest_call_helper(self, action_result, endpoint, verify=True, headers=None, params=None, data=None, json=None, method="get"):
        """ Function that helps setting REST call to the app.

        :param endpoint: REST endpoint that needs to appended to the service address
        :param action_result: object of ActionResult class
        :param headers: request headers
        :param params: request parameters
        :param data: request body
        :param json: JSON object
        :param method: GET/POST/PUT/DELETE/PATCH (Default will be GET)
        :param verify: verify server certificate (Default True)
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        response obtained by making an API call
        """

        url = f"{self._base_url}/api/v2/{endpoint}"
        if headers is None:
            headers = {}

        token = self._access_token
        if not token:
            ret_val = self._get_token(action_result)

            if phantom.is_fail(ret_val):
                return RetVal(action_result.get_status(), None)
        headers.update({
                'X-ESG-Auth-Token': self._access_token,
                'X-Switch-User': self._admin_user,
                'Content-Type': 'application/json'
            })
        ret_val, resp_json = self._make_rest_call(url, action_result, verify, headers, params, data, json, method)

        # If token is expired, generate a new token
        message = action_result.get_message()
        self.debug_print(f"message: {message}")
        if message and ('token' in message and 'expired' in message):
            self.save_progress("Token is invalid/expired. Hence, generating a new token.")
            ret_val = self._get_token(action_result)
            if phantom.is_fail(ret_val):
                return RetVal(ret_val, None)

            headers.update({'X-ESG-Auth-Token': self._access_token})

            ret_val, resp_json = self._make_rest_call(url, action_result, verify, headers, params, data, json, method)

        if phantom.is_fail(ret_val):
            return RetVal(ret_val, resp_json)

        return RetVal(phantom.APP_SUCCESS, resp_json)

    def _handle_generate_token(self, param):

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))
        ret_val = self._get_token(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self.save_progress(f"Completed action handler for: {self.get_action_identifier()}")
        return action_result.set_status(phantom.APP_SUCCESS, "Token generated")

    def _handle_test_connectivity(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # NOTE: test connectivity does _NOT_ take any parameters
        # i.e. the param dictionary passed to this handler will be empty.
        # Also typically it does not add any data into an action_result either.
        # The status and progress messages are more important.

        # if not self._access_token:
        #     self.save_progress(f"Token not in state file, obtaining token")
        #     ret_val = self._get_token(action_result)
        #     if phantom.is_fail(ret_val):
        #         return action_result.get_status()

        params = {
            "page": 1
        }
        endpoint = LIBRAESVA_MESSAGE_ENDPOINT

        self.save_progress("Connecting to endpoint")
        # make rest call
        ret_val, response = self._make_rest_call_helper(
            action_result, endpoint=endpoint, params=params, headers=None
        )

        if phantom.is_fail(ret_val):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # for now the return is commented out, but after implementation, return from here
            self.save_progress("Test Connectivity Failed.")
            return action_result.get_status()

        # Return success
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

        # For now return Error with a message, in case of success we don't set the message, but use the summary
        # return action_result.set_status(phantom.APP_ERROR, "Action not yet implemented")

    def _handle_search_email(self, param):

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        # if not self._access_token:
        #     self.save_progress(f"Token not in state file, obtaining token")
        #     ret_val = self._get_token(action_result)
        #     if phantom.is_fail(ret_val):
        #         return action_result.get_status()

        page = param.get('page', '')
        groups = param.get('groups', '')
        date_range = param.get('date_range', '')
        email = param.get('email', '')
        groups_value = param.get('groups_value', '')

        endpoint = LIBRAESVA_MESSAGE_ENDPOINT
        params = {}

        if page:
            params['page'] = page
        if groups:
            params['groups[0][queries][0][field]'] = groups
        if date_range:
            params['date_range'] = date_range
        if email:
            params['email'] = email
        if groups_value:
            params['groups[0][queries][0][value]'] = groups_value

        ret_val = self._handle_pagination(action_result, endpoint=endpoint, params=params, headers=None)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # action_result.add_data(response)

        summary = action_result.update_summary({})
        resp_data = action_result.get_data()
        if resp_data and resp_data[action_result.get_data_size() - 1] == 'Empty response':
            summary['num_messages'] = (action_result.get_data_size()) - 1
        else:
            summary['num_messages'] = action_result.get_data_size()

        self.save_progress(f"Completed action handler for: {self.get_action_identifier()}")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_blocklist_resource(self, param):

        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        from_param = param.get('from')
        to_param = param.get('to')
        only_envelope = param.get('only_envelope', False)

        data = {
            'from': from_param,
            'to': to_param,
            'onlyEnvelope': only_envelope
        }

        endpoint = LIBRAESVA_BLOCK_RESOURCE_ENDPOINT

        ret_val, _ = self._make_rest_call_helper(action_result, endpoint, json=data, method='post')

        if phantom.is_fail(ret_val):
            return ret_val

        summary = action_result.update_summary({})
        summary['status'] = "Successfully added element to blocklist"

        # An empty response indicates success. No response body is returned.
        self.save_progress(f"Completed action handler for: {self.get_action_identifier()}")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_token(self, action_result):
        """ This function is used to get a token via REST Call.

        :param action_result: Object of action result
        :return: status(phantom.APP_SUCCESS/phantom.APP_ERROR)
        """

        data = {
            'username': self._username,
            'password': self._password,
        }
        req_url = self._base_url + LIBRAESVA_LOGIN_ENDPOINT
        ret_val, resp_json = self._make_rest_call(req_url, action_result, headers=None, json=data, method='post')

        if phantom.is_fail(ret_val):
            self.save_progress("Error occured trying to obtain authorization token")
            return action_result.get_status()

        self.save_progress("Token obtained")

        self._access_token = resp_json.get('token', None)

        return phantom.APP_SUCCESS

    def _handle_pagination(self, action_result, endpoint, headers=None, params=None):
        """
        This action is used to create an iterator that will paginate through responses from called methods.

        :param action_result: Object of ActionResult class
        :param endpoint: REST endpoint that needs to appended to the service address
        :param headers: Dictionary of headers for the rest API calls
        :param params: Dictionary of params for the rest API calls
        """
        while True:
            # make rest call
            ret_val, response = self._make_rest_call_helper(action_result, endpoint, headers=headers, params=params, method='get')

            if phantom.is_fail(ret_val):
                return None

            if "_embedded" in response:
                for email in response.get('_embedded', []).get('item'):
                    action_result.add_data(email)
                if len(response.get('_embedded', []).get('item')) > 0 and response.get('_embedded').get('item') == {}:
                    action_result.add_data('Empty response')
            else:
                action_result.add_data(response)

            if response.get('_links').get('next'):
                next_url = response.get('_links').get('next').get('href')
                parsed_url = urlparse.urlparse(next_url)
                self.debug_print(f'PARSED URL {parsed_url}')
                try:
                    params['page'] += 1
                except Exception:
                    self.debug_print("Error occurred while extracting params from _links.next")
                    break
            else:
                break

        return phantom.APP_SUCCESS

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == 'test_connectivity':
            ret_val = self._handle_test_connectivity(param)
        if action_id == 'search_email':
            ret_val = self._handle_search_email(param)
        if action_id == 'blocklist_resource':
            ret_val == self._handle_blocklist_resource(param)

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()
        self._asset_id = self.get_asset_id()

        self._base_url = config.get('base_url')
        self._username = config.get('username')
        self._password = config.get('password')
        self._admin_user = config.get('admin_user')

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse
    import sys

    argparser = argparse.ArgumentParser()

    argparser.add_argument('input_test_json', help='Input Test JSON file')
    argparser.add_argument('-u', '--username', help='username', required=False)
    argparser.add_argument('-p', '--password', help='password', required=False)
    argparser.add_argument(
        "-v",
        "--verify",
        action="store_true",
        help="verify",
        required=False,
        default=False,
    )

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
            login_url = LibraesvaConnector._get_phantom_base_url() + '/login'

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify)
            csrftoken = r.cookies['csrftoken']

            data = dict()
            data['username'] = username
            data['password'] = password
            data['csrfmiddlewaretoken'] = csrftoken

            headers = dict()
            headers['Cookie'] = 'csrftoken=' + csrftoken
            headers['Referer'] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers)
            session_id = r2.cookies['sessionid']
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = LibraesvaConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json['user_session_token'] = session_id
            connector._set_csrf_info(csrftoken, headers['Referer'])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == '__main__':
    main()
