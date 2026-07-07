# --
# File: cyphort_connector.py
# Copyright (c) 2014-2021 Splunk Inc.
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

import time

# Phantom imports
import phantom.app as phantom
# Other imports used by this connector
import requests
import simplejson as json
from phantom.app import ActionResult, BaseConnector
from phantom.vault import Vault

from cyphort_consts import *


class CyphortConnector(BaseConnector):

    # The actions supported by this connector
    ACTION_ID_DETONATE_FILE = "detonate_file"
    ACTION_ID_SANDBOX_RESULTS = "get_report"

    def __init__(self):

        # Call the BaseConnectors init first
        super(CyphortConnector, self).__init__()

    def initialize(self):

        config = self.get_config()

        # Base URL
        self._base_url = CYPHORT_REST_API_URL.format(server=config[CYPHORT_JSON_SERVER])

        self._host = self._base_url[self._base_url.find('//') + 2:]

        self._headers = {'Authorization': config[CYPHORT_JSON_APIKEY]}

        return phantom.APP_SUCCESS

    def _make_post_rest_call(self, endpoint, action_result, request_params={}, data=None):

        resp_json = None
        status_code = None

        headers = self._headers

        config = self.get_config()

        try:
            r = requests.post(self._base_url + endpoint, data=data, headers=headers,  # nosemgrep:
                              params=request_params, verify=config[phantom.APP_JSON_VERIFY])
        except Exception as e:
            return (action_result.set_status(phantom.APP_ERROR, CYPHORT_ERR_SERVER_CONNECTION, e), resp_json, status_code)

        # self.debug_print('REST url: {0}'.format(r.url))

        try:
            resp_json = r.json()
            status_code = r.status_code
        except Exception:
            return (action_result.set_status(phantom.APP_ERROR, "Response not a valid json"), resp_json, status_code)

        if (not resp_json):
            return (action_result.set_status(phantom.APP_ERROR, "Empty response from server"), resp_json, status_code)

        if ('status' not in resp_json):
            return (action_result.set_status(phantom.APP_ERROR, "Status not set in response"), resp_json, status_code)

        status = resp_json['status']

        if (status_code != requests.codes.ok) or (status != 0):  # pylint: disable=E1101
            message = "Not set"
            if ('error_msg' in resp_json):
                message = resp_json['error_msg']
            elif('detail' in resp_json):
                message = resp_json['detail']

            return (action_result.set_status(phantom.APP_ERROR,
                CYPHORT_ERR_FROM_SERVER, status_code=status_code, status=status, message=message),
                resp_json, status_code)

        return (phantom.APP_SUCCESS, resp_json, status_code)

    def _detonate_file(self, param):

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        action_result = self.add_action_result(ActionResult(dict(param)))

        config = self.get_config()
        vault_id = param['vault_id']
        filename = param.get('file_name', vault_id)
        file_meta_json = {'file_name': filename}
        action_result.update_summary({CYPHORT_JSON_TARGET: filename})

        try:
            payload = open(Vault.get_file_path(vault_id), 'rb')
        except Exception:
          return action_result.set_status(phantom.APP_ERROR, 'File not found in vault ("{}")'.format(vault_id))

        files = {'file': (filename, payload), 'file_meta_json': json.dumps(file_meta_json)}

        upload_url = CYPHORT_REST_API_UPLOAD_FILE_URL.format(server=config[CYPHORT_JSON_SERVER])

        try:
            r = requests.post(upload_url, headers=self._headers, files=files, verify=config[phantom.APP_JSON_VERIFY])  # nosemgrep
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, CYPHORT_ERR_SERVER_CONNECTION, e)

        # self.debug_print('REST url: {0}'.format(r.url))

        try:
            resp_json = r.json()
            status_code = r.status_code
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, "Response not a valid json")

        if ('status' not in resp_json):
            return action_result.set_status(phantom.APP_ERROR, "Status not set in response")

        status = resp_json['status']

        if (status_code != requests.codes.ok) or (status != 0):  # pylint: disable=E1101

            message = "Not set"
            if ('error_msg' in resp_json):
                message = resp_json['error_msg']
            elif('detail' in resp_json):
                message = resp_json['detail']

            return action_result.set_status(phantom.APP_ERROR,
                                            CYPHORT_ERR_FROM_SERVER.format(
                                                status_code=status_code, status=status, message=message))

        self.save_progress(CYPHORT_MSG_FILE_SUBMITTED)

        if ('detail' not in resp_json):
            return action_result.set_status(phantom.APP_ERROR, "Response does not contain the 'details' key")

        details = resp_json['detail']

        if ('event_id' not in details):
            return action_result.set_status(phantom.APP_ERROR, "Response does not contain the 'event_id'")

        action_result.update_summary({CYPHORT_JSON_EVENT_ID: details['event_id']})

        return self._poll_for_event_completion(action_result, details['event_id'])

    def _poll_for_event_completion(self, action_result, event_id):

        data = {'event_id': event_id}

        completed_event = None

        # Poll CYPHORT_MAX_POLL_TIMES
        for x in xrange(CYPHORT_MAX_POLL_TIMES):

            self.save_progress(CYPHORT_MSG_POLL_TRY.format(x))

            ret_val, response, status_code = self._make_post_rest_call('', action_result,
                                                                       request_params={'op': 'event_details'}, data=data)

            if (phantom.is_fail(ret_val)):
                return action_result.get_status()

            if ('event_details' not in response or response['event_details'] is None):
                return action_result.set_status(phantom.APP_ERROR, "Event details not in response")

            event_details = response['event_details']

            if ('analysis_done_time' not in event_details):
                return action_result.set_status(phantom.APP_ERROR, "Analysis status info not in response")

            if (event_details['analysis_done_time'] is not None):
                completed_event = event_details
                break

            time.sleep(CYPHORT_POLL_SLEEP_SECS)

        if (completed_event is None):
            return action_result.set_status(phantom.APP_SUCCESS, CYPHORT_SUCC_ANALYSIS_INCOMPLETE)

        # The analysis is complete, now get the other details
        self.save_progress(CYPHORT_MSG_ANALYSIS_COMPLETE)

        return self._get_finished_event_details(action_result, event_id)

    def _get_finished_event_details(self, action_result, event_id):

        data = {'event_id': event_id}

        ret_val, response, status_code = self._make_post_rest_call('', action_result,
                                                                   request_params={'op': 'analysis_details'}, data=data)

        if (phantom.is_fail(ret_val)):
            return action_result.get_status()

        analysis_details = response

        ret_val, response, status_code = self._make_post_rest_call('', action_result,
                                                                   request_params={'op': 'behavior_details'}, data=data)

        if (phantom.is_fail(ret_val)):
            return action_result.get_status()

        behavior_details = response

        action_result.add_data({CYPHORT_JSON_ANALYSIS: analysis_details, CYPHORT_JSON_BEHAVIOR: behavior_details})

        # set the action result status to success, this is the last function that any action is going to call anyways
        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_detonation_result(self, param):

        action_result = self.add_action_result(ActionResult(dict(param)))

        return self._poll_for_event_completion(action_result, param[CYPHORT_JSON_ID])

    def _test_connectivity(self, param):

        # Progress
        self.save_progress(CYPHORT_USING_BASE_URL, base_url=self._base_url)

        # Connectivity
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, self._host)

        self.save_progress(CYPHORT_MSG_QUERYING_USERS_CHECK_CREDS)

        endpoint = ''

        action_result = ActionResult()

        ret_val, response, status_code = self._make_post_rest_call(endpoint, action_result, request_params={'op': 'get_users'})

        if (phantom.is_fail(ret_val)):
            self.debug_print(action_result.get_message())
            self.set_status(phantom.APP_ERROR, action_result.get_message())
            self.append_to_message(CYPHORT_ERR_CONNECTIVITY_TEST)
            return phantom.APP_ERROR

        return self.set_status_save_progress(phantom.APP_SUCCESS, CYPHORT_SUCC_CONNECTIVITY_TEST)

    def handle_action(self, param):
        """Function that handles all the actions

        Args:

        Return:
            A status code
        """

        action = self.get_action_identifier()

        if (action == self.ACTION_ID_DETONATE_FILE):
            result = self._detonate_file(param)
        elif (action == self.ACTION_ID_SANDBOX_RESULTS):
            result = self._get_detonation_result(param)
        elif (action == phantom.ACTION_ID_TEST_ASSET_CONNECTIVITY):
            result = self._test_connectivity(param)
        else:
          raise ValueError('action %r is not supported' % action)

        return result


if __name__ == '__main__':

    import sys

    # import simplejson as json
    import pudb

    pudb.set_trace()

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=' ' * 4))

        connector = CyphortConnector()
        connector.print_progress_message = True
        connector._handle_action(json.dumps(in_json), None)

    sys.exit(0)
