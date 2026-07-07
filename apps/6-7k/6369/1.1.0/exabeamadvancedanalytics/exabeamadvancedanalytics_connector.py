# File: exabeamadvancedanalytics_connector.py
#
# Copyright (c) 2022 Splunk Inc.
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

# Phantom App imports
import json

import phantom.app as phantom
# Usage of the consts file is recommended
# from exabeamadvanacedanalytics_consts import *
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector


class RetVal(tuple):
    def __new__(cls, val1, val2):
        return tuple.__new__(RetVal, (val1, val2))


class ExabeamAdvanacedAnalyticsConnector(BaseConnector):

    def __init__(self):

        # Call the BaseConnectors init first
        super(ExabeamAdvanacedAnalyticsConnector, self).__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._base_url = None

    def _process_empty_reponse(self, response, action_result):

        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        error_text = "Empty response with status {} and no information in the header".format(response.status_code)

        return RetVal(action_result.set_status(phantom.APP_ERROR, error_text), None)

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

        message = "Status Code: {0}. Data from server:\n{1}\n".format(status_code,
                                                                      error_text)

        message = message.replace('{', '{{').replace('}', '}}')

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):

        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            error_text = "Unable to parse JSON response. Error: {0}".format(str(e))
            return RetVal(action_result.set_status(phantom.APP_ERROR, error_text), None)

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # the exabeam api doesn't return json errors, but leave this here just in case
        message = "Error from server. Status Code: {0} Data from server: {1}".format(
                r.status_code, r.text.replace('{', '{{').replace('}', '}}'))

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

        # Process an HTML resonse, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if 'html' in r.headers.get('Content-Type', ''):
            return self._process_html_response(r, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text:
            return self._process_empty_reponse(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {0} Data from server: {1}".format(
                r.status_code, r.text.replace('{', '{{').replace('}', '}}'))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, headers=None, params=None, data=None, method="get"):

        if not headers:
            headers = {}
        if 'Accept' not in headers:
            headers['Accept'] = 'application/json'

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            error_text = "Invalid method: {0}".format(method)
            return RetVal(action_result.set_status(phantom.APP_ERROR, error_text), None)

        # Create a URL to connect to
        url = self._base_url + endpoint

        try:
            r = request_func(
                            url,
                            auth=(self._username, self._password),
                            data=data,
                            headers=headers,
                            verify=self._verify_server_cert,
                            params=params)
        except Exception as e:
            error_text = "Error Connecting to server. Details: {0}".format(str(e))
            return RetVal(action_result.set_status(phantom.APP_ERROR, error_text), None)

        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param):

        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress('Connecting to endpoint and requesting watchlists')

        ret_val, response = self._make_rest_call('/watchlist', action_result, params=None, headers=None)

        if (phantom.is_fail(ret_val)):
            self.save_progress("Test Connectivity Failed. Error: {0}".format(action_result.get_message()))
            return action_result.get_status()

        # Return success
        watchlist_count = len(response.get('users', []))
        self.save_progress('Found {} watchlist{}'.format(watchlist_count, 's' if watchlist_count != 1 else ''))
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_search_assets(self, param):

        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary
        params = {
            'keyword': param['keyword'],
            'limit': param.get('limit', 100)
        }

        # make rest call
        ret_val, response = self._make_rest_call('/search/assets', action_result, params=params, headers=None)

        if (phantom.is_fail(ret_val)):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary['matches'] = len(response.get('assets', []))

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_asset(self, param):

        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary
        assetId = param.get('hostname', param.get('ip'))
        if assetId is None:
            return action_result.set_status(phantom.APP_ERROR, 'One of ip or hostname must be specified')

        # make rest call
        ret_val, response = self._make_rest_call('/asset/{}/data'.format(assetId),
                                                 action_result,
                                                 params=None,
                                                 headers=None)

        if (phantom.is_fail(ret_val)):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            return action_result.get_status()

        if 'labels' in response:
            response['labels'] = [{'label': x} for x in response['labels']]
        if 'topTalkers' in response.get('topUsers', {}).get('hist', {}):
            response['topUsers']['hist']['topTalkers'] = [{'topTalker': x} for x in response['topUsers']['hist']['topTalkers']]
        if 'topTalkers' in response.get('topUsers', {}).get('smoothedHist', {}):
            response['topUsers']['smoothedHist']['topTalkers'] = [{'topTalker': x} for x in response['topUsers']['smoothedHist']['topTalkers']]
        if 'topTalkers' in response.get('topGroups', {}).get('hist', {}):
            response['topGroups']['hist']['topTalkers'] = [{'topTalker': x} for x in response['topGroups']['hist']['topTalkers']]
        if 'topTalkers' in response.get('topGroups', {}).get('smoothedHist', {}):
            response['topGroups']['smoothedHist']['topTalkers'] = [{'topTalker': x} for x in response['topGroups']['smoothedHist']['topTalkers']]

        # Add the response into the data section
        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_user(self, param):

        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary
        username = param['username']

        # make rest call
        ret_val, response = self._make_rest_call('/user/{}/info'.format(username),
                                                 action_result,
                                                 params=None,
                                                 headers=None)

        if (phantom.is_fail(ret_val)):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            return action_result.get_status()

        if 'pastScores' in response.get('userInfo', {}):
            response['userInfo']['pastScores'] = ', '.join(response['userInfo']['pastScores'])
        if 'labels' in response.get('userInfo', {}):
            response['userInfo']['labels'] = [{'label': x} for x in response['userInfo']['labels']]
        if 'accountNames' in response:
            response['accountNames'] = [{'accountName': x} for x in response['accountNames']]
        if 'pastScores' in response.get('managerInfo', {}):
            response['managerInfo']['pastScores'] = ', '.join(response['managerInfo']['pastScores'])
        if 'labels' in response.get('managerInfo', {}):
            response['managerInfo']['labels'] = [{'label': x} for x in response['managerInfo']['labels']]

        # Add the response into the data section
        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_search_users(self, param):

        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary
        params = {
            'keyword': param['keyword'],
            'limit': param.get('limit', 100)
        }

        # make rest call
        ret_val, response = self._make_rest_call('/search/users', action_result, params=params, headers=None)

        if (phantom.is_fail(ret_val)):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            return action_result.get_status()

        for user in response.get('users', []):
            if 'pastScores' in user:
                user['pastScores'] = ', '.join(user['pastScores'])
            if 'labels' in user:
                user['labels'] = [{'label': x} for x in user['labels']]

        # Add the response into the data section
        action_result.add_data(response)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary['matches'] = len(response.get('users', []))

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_watchlist(self, param):

        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary
        watchlist_id = param['watchlist_id']

        # make rest call
        ret_val, response = self._make_rest_call('/watchlist/{}/'.format(watchlist_id),
                                                 action_result,
                                                 params=None,
                                                 headers=None)

        if (phantom.is_fail(ret_val)):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            return action_result.get_status()

        for user in response.get('users', []):
            if 'pastScores' in user.get('user', {}):
                user['user']['pastScores'] = ', '.join(user['user']['pastScores'])
            if 'labels' in user.get('user', {}):
                user['user']['labels'] = [{'label': x} for x in user['user']['labels']]

        # Add the response into the data section
        action_result.add_data(response)

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary['users'] = len(response.get('users', []))

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_watchlists(self, param):

        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # make rest call
        ret_val, response = self._make_rest_call('/watchlist', action_result, params=None, headers=None)

        if (phantom.is_fail(ret_val)):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data({'watchlists': response})

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})
        summary['matches'] = len(response.get('users', []))

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_unwatch_user(self, param):

        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary
        username = param['username']
        data = {
            'watchlistId': param['watchlist_id']
        }

        # make rest call
        ret_val, response = self._make_rest_call('/watchlist/user/{}/remove'.format(username),
                                                 action_result,
                                                 params=None,
                                                 headers=None,
                                                 method='put',
                                                 data=data)

        if (phantom.is_fail(ret_val)):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_watch_user(self, param):

        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary
        username = param['username']
        data = {
            'watchlistId': param['watchlist_id']
        }
        if 'duration' in param:
            data['duration'] = param['duration']

        # make rest call
        ret_val, response = self._make_rest_call('/watchlist/user/{}/add'.format(username),
                                                 action_result,
                                                 params=None,
                                                 headers=None,
                                                 method='put',
                                                 data=data)

        if (phantom.is_fail(ret_val)):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            return action_result.get_status()

        # Add the response into the data section
        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):

        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == 'test_connectivity':
            ret_val = self._handle_test_connectivity(param)

        elif action_id == 'search_assets':
            ret_val = self._handle_search_assets(param)

        elif action_id == 'get_asset':
            ret_val = self._handle_get_asset(param)

        elif action_id == 'get_user':
            ret_val = self._handle_get_user(param)

        elif action_id == 'search_users':
            ret_val = self._handle_search_users(param)

        elif action_id == 'get_watchlist':
            ret_val = self._handle_get_watchlist(param)

        elif action_id == 'list_watchlists':
            ret_val = self._handle_list_watchlists(param)

        elif action_id == 'unwatch_user':
            ret_val = self._handle_unwatch_user(param)

        elif action_id == 'watch_user':
            ret_val = self._handle_watch_user(param)

        return ret_val

    def initialize(self):

        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        config = self.get_config()

        self._base_url = config['base_url']
        self._verify_server_cert = config['verify_server_cert']
        self._username = config['username']
        self._password = config['password']

        return phantom.APP_SUCCESS

    def finalize(self):

        # Save the state, this data is saved accross actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


if __name__ == '__main__':

    import argparse
    import sys

    import pudb

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument('input_test_json', help='Input Test JSON file')
    argparser.add_argument('-u', '--username', help='username', required=False)
    argparser.add_argument('-p', '--password', help='password', required=False)
    argparser.add_argument('-v', '--verify', action='store_true', help='verify', required=False, default=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password
    verify = args.verify

    if (username is not None and password is None):

        # User specified a username but not a password, so ask
        import getpass
        password = getpass.getpass("Password: ")

    if (username and password):
        try:
            print("Accessing the Login page")
            r = requests.get("https://127.0.0.1/login", verify=verify, timeout=30)
            csrftoken = r.cookies['csrftoken']

            data = dict()
            data['username'] = username
            data['password'] = password
            data['csrfmiddlewaretoken'] = csrftoken

            headers = dict()
            headers['Cookie'] = 'csrftoken=' + csrftoken
            headers['Referer'] = 'https://127.0.0.1/login'

            print("Logging into Platform to get the session id")
            r2 = requests.post("https://127.0.0.1/login", verify=verify, data=data, headers=headers, timeout=30)
            session_id = r2.cookies['sessionid']
        except Exception as e:
            print("Unable to get session id from the platfrom. Error: " + str(e))
            sys.exit(1)

    if (len(sys.argv) < 2):
        print("No test json specified as input")
        sys.exit(0)

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = ExabeamAdvanacedAnalyticsConnector()
        connector.print_progress_message = True

        if (session_id is not None):
            in_json['user_session_token'] = session_id

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
