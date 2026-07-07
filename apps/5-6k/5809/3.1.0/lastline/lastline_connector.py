# File: lastline_connector.py
#
# Copyright (c) 2015-2023 Splunk Inc.
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
import hashlib
import json
import sys
import time
# Other imports used by this connector
from datetime import datetime

import phantom.app as phantom
import phantom.rules as phrules
import requests
from phantom.app import ActionResult, BaseConnector
from phantom.vault import Vault as Vault

from lastline_consts import *
from llmodule.analysis_apiclient import ANALYSIS_API_NO_RESULT_FOUND, AnalysisAPIError, AnalysisClient


class LastlineConnector(BaseConnector):

    # The actions supported by this connector
    ACTION_ID_QUERY_FILE = "query_file"
    ACTION_ID_QUERY_URL = "query_url"
    ACTION_ID_SANDBOX_RESULTS = "get_detonation_result"
    ACTION_ID_GET_ARTIFACT = "get_artifact"

    def __init__(self):

        # Call the BaseConnectors init first
        super(LastlineConnector, self).__init__()

        self._client = None
        self._account_name = None
        self._report_url = None
        self._is_url_detonation = 0
        self._results_url_template = None

    def initialize(self):

        config = self.get_config()
        self._client = AnalysisClient(
            config['base_url'], config['license_key'],
            config['api_token'], verify_ssl=config.get('verify_server_cert', True)
        )
        self._account_name = config.get('account_username')
        self._report_url = config.get('report_url', 'https://user.lastline.com').rstrip('/')
        self._results_url_template = "{0}{1}".format(self._report_url, '/portal#/analyst/task/{}')

        return phantom.APP_SUCCESS

    def _update_report(self, response, report):

        score = None
        try:
            score = response['data']['tasks'][0]['score']
        except:
            pass

        try:
            score = response['data']['score']
        except:
            pass
        if score is not None:
            report['score'] = score

        sha1 = None
        try:
            sha1 = response['data']['tasks'][0]['file_sha1']
        except:
            pass

        try:
            sha1 = response['data']['analysis_subject']['sha1']
        except:
            pass

        if sha1:
            report['sha1'] = sha1

        mime_type = None

        try:
            mime_type = response['data']['analysis_subject']['mime_type']
        except:
            pass

        if mime_type:
            report['mime_type'] = mime_type

        malicious_activity = None

        try:
            malicious_activity = response['data']['malicious_activity']
        except:
            pass

        if malicious_activity:
            malicious_activity = [{'type': x.split(':')[0], 'description': x.split(':')[1]} for x in malicious_activity]
            report['malicious_activity'] = malicious_activity

        threat = None

        try:
            threat = response['data']['threat']
        except:
            pass

        if threat:
            report['threat'] = threat

        threat_class = None

        try:
            threat_class = response['data']['threat_class']
        except:
            pass

        if threat_class:
            report['threat_class'] = threat_class

        if self._is_url_detonation:
            try:
                report[ANALYSIS_KEY]['subject']['url'] = response['data']['analysis_subject']['url']
            except:
                self.debug_print("Exception in setting url")

    def _poll_task_status(self, task_id, action_result, task_start_time=None):

        if not task_start_time:
            task_start_time = datetime(1970, 1, 1)

        polling_attempt = 0

        config = self.get_config()

        timeout = int(config.get(LASTLINE_JSON_POLL_TIMEOUT_SECS, LASTLINE_MAX_TIMEOUT_DEF_SECS))

        if timeout < LASTLINE_SLEEP_SECS:
            return (action_result.set_status(phantom.APP_ERROR,
                                             "Please specify timeout greater than {0}".format(LASTLINE_SLEEP_SECS)), None)

        max_polling_attempts = (timeout / LASTLINE_SLEEP_SECS)

        while polling_attempt < max_polling_attempts:

            polling_attempt += 1

            self.save_progress("Polling attempt {0} of {1}".format(polling_attempt, max_polling_attempts))

            report = None

            try:
                response = self._client.get_result(task_id)
                report = response.get('data', {}).get(RESULT_REPORT_KEY)
            except AnalysisAPIError as e:
                self.debug_print("Got AnalysisAPIError exception:", str(e))
                no_result_found = bool(e.error_code == ANALYSIS_API_NO_RESULT_FOUND)
                if not no_result_found:
                    return action_result.set_status(phantom.APP_ERROR, LASTLINE_ERROR_GETTING_REPORT, e), None
            except Exception as e:
                self.debug_print("Got Exception: ", e)
                return action_result.set_status(phantom.APP_ERROR, LASTLINE_ERROR_GETTING_REPORT, e), None

            if report:
                self._update_report(response, report)
                return phantom.APP_SUCCESS, report

            time.sleep(LASTLINE_SLEEP_SECS)

        self.save_progress("Reached max polling attempts.")

        return phantom.APP_SUCCESS, None

    def _get_target(self, report):

        # target is different thing depending on the type of detonation; url or file
        # unfortunately in case 'get result' we don't know what type of detonation it was

        # if url is present return that
        if self._is_url_detonation:
            try:
                return "url", report[ANALYSIS_KEY]['subject']['url']
            except:
                return "url", 'Unknown'

        else:
            # it's a file detonation, so need to get in roundabout way
            try:
                entry = report[ANALYSIS_SUBJECT_KEY][0]
                subj_id = entry.get('overview', {}).get('process', {}).get('analysis_subject_id')
                this_id = entry.get('overview', {}).get('id')
                if subj_id == this_id:
                    target = entry.get('process', {}).get('executable', {}).get('static_pe_information', {}).get('original_filename')
                    if not target:
                        target = entry.get('overview', {}).get('process', {}).get('executable', {}).get('filename', '').split('\\')[-1]
            except Exception as e:
                self.debug_print("Handled File Exception: ", e)
            return 'file', 'Unknown'

    def _update_report_summary(self, report, action_result, task_id):

        action_result.add_data({RESULT_REPORT_KEY: report})

        result_url = self._results_url_template.format(task_id)

        analysis_type, target = self._get_target(report)

        action_result.update_summary({TASK_ID_KEY: task_id,
            RESULTS_URL_KEY: result_url, SUMMARY_TYPE_KEY: analysis_type, TARGET_KEY: target})

        if 'score' in report:
            action_result.update_summary({'score': report['score']})

        return phantom.APP_SUCCESS

    def _poll_task_parse_report(self, task_id, action_result, report=None, task_start_time=None):

        if report is None:

            # first poll for the task status
            ret_val, report = self._poll_task_status(task_id, action_result, task_start_time)

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            if not report:
                return action_result.set_status(phantom.APP_ERROR, LASTLINE_POLL_TIMEOUT.format(task_id))

        ret_val = self._update_report_summary(report, action_result, task_id)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS)

    def _get_detonation_result(self, param):

        action_result = self.add_action_result(ActionResult(param))
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        task_id = param[TASK_ID_KEY]
        action_result.update_summary({TASK_ID_KEY: task_id, RESULTS_URL_KEY: self._results_url_template.format(task_id)})

        return self._poll_task_parse_report(task_id, action_result)

    def _get_task_id(self, response, action_result):

        task_id = None

        # Now get the data key, should be always present in a success result
        data = response.get('data')

        if not data:
            return action_result.set_status(phantom.APP_ERROR, "Data key not found in response. API failed"), None, None

        # Check for errors, if present then the call failed
        errors = data.get('errors')

        if errors:
            errors = '. '.join(errors)
            return (action_result.set_status(phantom.APP_ERROR, "API failed. Error: {0}".format(errors)), None, None)

        # now check for success status
        if response.get('success') != 1:
            return action_result.set_status(phantom.APP_ERROR, "API call failed"), None, None

        # Now try to get the task uuid as if it was a detonation call
        task_id = data.get('task_uuid')
        report = data.get('report')

        if report:
            self._update_report(response, report)

        if task_id:
            return phantom.APP_SUCCESS, task_id, report

        # it's not at the location of a detonation result, now check if it is present at
        # the location of a query hash
        if data.get('files_found', 0) > 0:
            try:
                return phantom.APP_SUCCESS, data['tasks'][0]['task_uuid'], report
            except Exception as e:
                self.debug_print("Handled Exception:", e)

        return phantom.APP_ERROR, None, None

    def _query_url(self, param):
        self._is_url_detonation = 1
        action_result = self.add_action_result(ActionResult(param))
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        task_start_time = datetime.utcnow()

        try:
            response = self._client.submit_url(param['url'], push_to_portal_account=self._account_name)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, LASTLINE_ERROR_SUBMIT_URL, e)

        ret_val, task_id, report = self._get_task_id(response, action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.update_summary({TASK_ID_KEY: task_id, RESULTS_URL_KEY: self._results_url_template.format(task_id),
                                      TARGET_KEY: param['url'], SUMMARY_TYPE_KEY: ANALYSIS_TYPE_URL})

        if not report:
            # Sleep for few seconds before querying the results. Gives the server some time and results in less failures.
            time.sleep(2)

        return self._poll_task_parse_report(task_id, action_result, report, task_start_time)

    def _get_vault_file_info(self, action_result, vault_id):

        try:
            success, message, vault_info = phrules.vault_info(vault_id=vault_id)
            vault_info = list(vault_info)[0]
        except IndexError:
            return action_result.set_status(phantom.APP_ERROR, VAULT_ERROR_FILE_NOT_FOUND), None
        except Exception:
            return action_result.set_status(phantom.APP_ERROR, VAULT_ERROR_INVALID_VAULT_ID), None

        return phantom.APP_SUCCESS, vault_info

    def _query_file(self, param):

        action_result = self.add_action_result(ActionResult(param))
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        vault_id = param['vault_id']
        filename = param.get('file_name')
        force_analysis = param.get('force_analysis')
        task_id = None

        task_start_time = datetime.utcnow()

        # First try to query the file as is, without uploading, if lastline has results for it
        try:
            response = self._client.query_file_hash(sha256=vault_id)
        except Exception as e:
            self.debug_print("Exception on query_file {0}".format(str(e)))
            return action_result.set_status(phantom.APP_ERROR, "Error Querying file hash", e)

        # get the task id
        ret_val, task_id, report = self._get_task_id(response, action_result)

        if phantom.is_success(ret_val):
            # we got a task id, means hash already present, get the result
            return self._poll_task_parse_report(task_id, action_result, report)

        # New hash, will need to upload the bytes
        ret_val, file_info = self._get_vault_file_info(action_result, vault_id)
        if phantom.is_fail(ret_val):
            return ret_val

        try:
            payload = open(file_info['path'], 'rb')
        except:
            return action_result.set_status(phantom.APP_ERROR, 'File not found in vault ("{}")'.format(vault_id))

        # Submit it to the cloud
        try:
            response = self._client.submit_file(payload,
                                                bypass_cache=force_analysis,
                                                delete_after_analysis=None,
                                                filename=filename,
                                                push_to_portal_account=self._account_name)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, str(e))

        # Get the task id
        ret_val, task_id, report = self._get_task_id(response, action_result)

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, LASTLINE_ERROR_TASK_ID_NOT_FOUND)

        summary = {TASK_ID_KEY: task_id, RESULTS_URL_KEY: self._results_url_template.format(task_id),
                   SUMMARY_TYPE_KEY: ANALYSIS_TYPE_FILE, TARGET_KEY: vault_id}

        action_result.update_summary(summary)

        if not report:
            # Sleep for few seconds before querying the results. Gives the server some time and results in less failures.
            time.sleep(2)

        return self._poll_task_parse_report(task_id, action_result, report, task_start_time)

    def _test_connectivity(self, param):

        # Create a hash of a random string
        random_string = phantom.get_random_chars(size=10)

        config = self.get_config()

        timeout = int(config.get(LASTLINE_JSON_POLL_TIMEOUT_SECS, LASTLINE_MAX_TIMEOUT_DEF_SECS))

        if timeout < LASTLINE_SLEEP_SECS:
            self.save_progress(LASTLINE_ERROR_CONNECTIVITY_TEST)
            return (self.set_status(phantom.APP_ERROR,
                                    "Please specify timeout greater than {0}".format(LASTLINE_SLEEP_SECS)), None)
        sha256_hash = hashlib.sha256(random_string.encode('utf-8')).hexdigest()

        self.save_progress(LASTLINE_GENERATED_RANDOM_HASH, gen_hash=sha256_hash)

        try:
            self._client.query_file_hash(sha256=sha256_hash)
        except Exception as e:
            self.save_progress(str(e))
            return self.set_status(phantom.APP_ERROR, LASTLINE_ERROR_CONNECTIVITY_TEST)

        self.save_progress(LASTLINE_SUCCESS_CONNECTIVITY_TEST)
        return self.set_status(phantom.APP_SUCCESS)

    def _get_artifact(self, param):

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))

        task_id = param['id']
        artifact_name = param.get('artifact_name')
        artifact_password = param.get('password')
        container_id = param.get('container_id')
        if not container_id:
            container_id = self.get_container_id()

        # Get Report
        ret_val, report = self._poll_task_status(task_id, action_result, task_start_time=None)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        if not report:
            return action_result.set_status(phantom.APP_ERROR, LASTLINE_POLL_TIMEOUT.format(task_id))

        if 'analysis_metadata' not in report or not isinstance(report['analysis_metadata'], list):
            return action_result.set_status(phantom.APP_ERROR, "No analysis metadata in report")

        artifact_names = [artifact['name'] for artifact in report['analysis_metadata']]

        if artifact_name:
            if artifact_name in artifact_names:
                artifact_names = [artifact_name]
            else:
                error_message = f"Requested artifact not found, report provides: {', '.join(artifact_names)}"
                self.save_progress(error_message)
                action_result.add_data({'error': error_message})
                return action_result.set_status(phantom.APP_ERROR, error_message)

        self.save_progress(f"Downloading the following artifacts: {json.dumps(artifact_names)}")
        summary = {
            TASK_ID_KEY: task_id,
            RESULTS_URL_KEY: self._results_url_template.format(task_id),
            SUMMARY_TYPE_KEY: ANALYSIS_TYPE_FILE,
            VAULT_ARTIFACTS_STORED_KEY: 0,
            VAULT_ARTIFACTS_FAILED_KEY: 0,
            VAULT_ARTIFACTS_TOTAL_KEY: 0
        }

        downloaded_files = set()
        for artifact in report['analysis_metadata']:
            file_name = artifact['name']
            if file_name not in artifact_names or file_name in downloaded_files:
                continue

            downloaded_files.add(file_name)
            summary[VAULT_ARTIFACTS_TOTAL_KEY] = summary[VAULT_ARTIFACTS_TOTAL_KEY] + 1
            artifact_result = self._client.get_report_artifact(task_id, report['uuid'], file_name, artifact_password)
            artifact_value = artifact_result.getvalue()
            report_subject = ""
            try:
                if 'analysis' in report:
                    url = report['analysis']['network']['requests'][0]['url']
                    artifact['url'] = url
                    report_subject = ''.join(e if e.isalnum() else '_' for e in url)
                if 'analysis_subjects' in report:
                    source_file = report['analysis_subjects'][0]['process']['arguments'].split('\\')[-1]
                    artifact['source_file'] = source_file
                    report_subject = source_file
            except:
                pass

            file_name = f"{report_subject}_{task_id}_{self.get_app_run_id()}_{file_name}"
            vault_response = Vault.create_attachment(artifact_value, container_id, file_name=file_name)
            artifact.update(vault_response)
            artifact['task_id'] = task_id
            artifact['name'] = file_name
            artifact['file_name'] = file_name

            if vault_response.get('succeeded'):
                summary[VAULT_ARTIFACTS_STORED_KEY] = summary[VAULT_ARTIFACTS_STORED_KEY] + 1
                artifact['vault_state'] = 'stored'
            else:
                summary[VAULT_ARTIFACTS_FAILED_KEY] = summary[VAULT_ARTIFACTS_FAILED_KEY] + 1
                artifact['vault_state'] = 'error'
            action_result.add_data(artifact)

        action_result.update_summary(summary)

        if summary[VAULT_ARTIFACTS_STORED_KEY] == summary[VAULT_ARTIFACTS_TOTAL_KEY]:
            return action_result.set_status(phantom.APP_SUCCESS, "All artifacts stored successfully")
        else:
            return action_result.set_status(phantom.APP_ERROR, "Some Artifacts could not be stored")

    def handle_action(self, param):
        """Function that handles all the actions

        Args:

        Return:
            A status code
        """

        action = self.get_action_identifier()
        result = phantom.APP_SUCCESS

        if action == self.ACTION_ID_QUERY_FILE:
            result = self._query_file(param)
        elif action == self.ACTION_ID_QUERY_URL:
            result = self._query_url(param)
        elif action == self.ACTION_ID_SANDBOX_RESULTS:
            result = self._get_detonation_result(param)
        elif action == phantom.ACTION_ID_TEST_ASSET_CONNECTIVITY:
            result = self._test_connectivity(param)
        elif action == self.ACTION_ID_GET_ARTIFACT:
            result = self._get_artifact(param)

        return result


if __name__ == '__main__':
    import argparse

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

    if username is not None and password is None:
        # User specified a username but not a password, so ask
        import getpass

        password = getpass.getpass("Password: ")

    if username and password:
        try:
            login_url = LastlineConnector._get_phantom_base_url() + '/login'

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=LASTLINE_DEFAULT_TIMEOUT)
            csrftoken = r.cookies['csrftoken']

            data = dict()
            data['username'] = username
            data['password'] = password
            data['csrfmiddlewaretoken'] = csrftoken

            headers = dict()
            headers['Cookie'] = 'csrftoken=' + csrftoken
            headers['Referer'] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, timeout=LASTLINE_DEFAULT_TIMEOUT,
                               data=data, headers=headers)
            session_id = r2.cookies['sessionid']
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = LastlineConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json['user_session_token'] = session_id
            connector._set_csrf_info(csrftoken, headers['Referer'])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
