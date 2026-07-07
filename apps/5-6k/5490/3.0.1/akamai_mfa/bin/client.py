import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from enum import Enum

import requests
import urllib3

import constants
import log as logging
import user_agent
from baseconfig import AkamaiMfaConfig, AuthsConfig, ResourceConfig, SessionHistoryConfig

LOG = logging.getLogger(__name__)

# Always true. Set environment variable AKAMAI_MFA_VERIFY_SSL to false for local SSL domain.
# ENV NOT SET        -> True (default)
# "true" / "TRUE"    -> True
# "false" / "FALSE"  -> False
# Any other value    -> True  (typos must NOT disable SSL)
VERIFY_SSL = os.getenv("AKAMAI_MFA_VERIFY_SSL", "true").lower() != "false"
if not VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ApiResponseAction(Enum):
    NoMoreDataPresent = 0
    MoreDataPresent = 1
    ErrorOccurred = 2


class ApiResponse:
    def __init__(self, action: ApiResponseAction, token: str = None):
        self.action = action
        self.token = token


class AkamaiMfaClient(object):

    def __init__(self):
        self._content_type_json = {'content-type': 'application/json'}
        self._content_type_form = {
            'content-type': 'application/x-www-form-urlencoded'}
        self._headers = None
        self.config = AkamaiMfaConfig.load_from_file()
        self.offset = None
        self._user_agent = user_agent.get_user_agent_details()

    @staticmethod
    def get_signature(offsetted_unix_time_str, secret_access_key):
        signature = hmac.new(
            key=secret_access_key.encode("utf-8"),
            msg=str(offsetted_unix_time_str).encode("utf-8"),
            digestmod=hashlib.sha256).hexdigest()

        return signature

    def ensure_signature_in_header(self, api_key, secret_key):
        splunk_server_unix_time = int(time.time())
        offsetted_unix_time_str = str(splunk_server_unix_time + self.offset)

        LOG.info(
            f"Generating signature with timestamp: {offsetted_unix_time_str}, splunk server unix time: {splunk_server_unix_time}, offset: {self.offset}")
        signature = self.get_signature(
            offsetted_unix_time_str, secret_access_key=secret_key)

        self._headers = {
            'X-Pushzero-Id': api_key,
            'X-Pushzero-Signature': signature,
            'X-Pushzero-Signature-Time': offsetted_unix_time_str,
            'X-Api-Version': constants.api_version_date
        }

        if self._user_agent:
            self._headers['X-Mfa-Ua'] = self._user_agent

        self._headers.update(self._content_type_json)

    def mfa_server_time(self):
        """Fetches the MFA server time"""
        LOG.info("Getting MFA server time")
        try:
            api_url = '{}/api/{}/time'.format(
                self.config.host,
                constants.api_version
            )

            resp = requests.get(
                api_url,
                headers=self._content_type_json,
                verify=VERIFY_SSL
            )

            if resp.status_code != requests.codes.ok:
                LOG.error(f"MFA server error: {resp.text}")
                return None

            resp_json = json.loads(resp.text)
            mfa_server_unix_timestamp = resp_json.get("result").get("unix_timestamp", None)
            if mfa_server_unix_timestamp is not None:
                mfa_server_time = datetime.fromtimestamp(mfa_server_unix_timestamp, tz=timezone.utc)
                splunk_server_time = int(time.time())
                self.offset = int(mfa_server_unix_timestamp) - splunk_server_time
                LOG.info(f"Current time: mfa_server={mfa_server_time}, splunk={datetime.now(timezone.utc)}")
                LOG.info(
                    f"Unix time: mfa_server={mfa_server_unix_timestamp}, splunk={splunk_server_time}, offset={self.offset}")
                return mfa_server_time
            else:
                LOG.error("Variable 'unix_timestamp' not present in response.")
                return None

        except Exception as ex:
            LOG.error(f"Exception while getting MFA server time. Exception: {ex}")
            return None

    def auths(self, params, continuation_token):
        LOG.info(f"Fetching auths: host={self.config.host}, app_id={self.config.app_id}, params={params}, continuation_token={continuation_token}")
        try:
            """Fetches the logs for given query params"""
            api_url = '{}/api/{}/control/reports/auths'.format(
                self.config.host,
                constants.api_version
            )

            # Handles empty string and None
            if continuation_token:
                request_body_data = json.dumps({
                    'continuation_token': continuation_token
                })
            else:
                request_body_data = json.dumps({})

            self.ensure_signature_in_header(
                api_key=self.config.app_id, secret_key=self.config.signing_key)

            # TODO use context manager 'with' statement to ensure response is closed reliably
            response = requests.post(
                api_url,
                request_body_data,
                params=params,
                headers=self._headers,
                verify=VERIFY_SSL
            )

            if response.status_code != requests.codes.ok:
                LOG.error(f"MFA server error: {response.text}")
                return ApiResponse(ApiResponseAction.ErrorOccurred)

            response_json = json.loads(response.text)
            result = response_json.get('result')
            data = result.get('data')
            data_len = len(data)
            LOG.info(f"Total number of auth records in response: {data_len}")

            if data_len > 0:
                for i in data:
                    print("\n", json.dumps(i))

            if 'continuation_token' in result:
                action = ApiResponseAction.MoreDataPresent
                next_min_time = params.get("min_time")
                next_max_time = params.get("max_time")
                next_page_size = params.get("page_size")
                next_continuation_token = result.get('continuation_token')
            else:
                action = ApiResponseAction.NoMoreDataPresent
                next_min_time = params.get("max_time")
                next_max_time = None
                next_page_size = constants.auths_page_size
                next_continuation_token = None

            LOG.info(f"Updating AuthsConfig: min_time={next_min_time}, continuation_token={next_continuation_token}")
            AuthsConfig(
                min_time=next_min_time,
                max_time=next_max_time,
                page_size=next_page_size,
                continuation_token=next_continuation_token
            ).save_to_file()

            response.close()
            return ApiResponse(action, next_continuation_token)
        except Exception as ex:
            LOG.error(f"Exception in auths script. Exception: {ex}")
            return ApiResponse(ApiResponseAction.ErrorOccurred)

    def session_history(self, params):
        LOG.info(f"Fetching session history: host={self.config.host}, app_id={self.config.app_id}, params={params}")
        try:
            """Fetches the session history for given query params"""
            api_url = '{}/api/{}/control/reports/session_history/flat'.format(
                self.config.host,
                constants.api_version
            )

            self.ensure_signature_in_header(
                api_key=self.config.app_id, secret_key=self.config.signing_key)

            # TODO use context manager 'with' statement to ensure response is closed reliably
            response = requests.get(
                api_url,
                params=params,
                headers=self._headers,
                verify=VERIFY_SSL
            )

            if response.status_code != requests.codes.ok:
                LOG.error(f"MFA server error: {response.text}")
                return ApiResponse(ApiResponseAction.ErrorOccurred)

            response_json = json.loads(response.text)
            page_data = response_json.get('result').get('page')
            page_len = len(page_data)
            LOG.info(f"Total number of session history records in response: {page_len}")

            if page_data:
                for item in page_data:
                    print("\n", json.dumps(item))

            if page_len == params.get("max_items"):
                action = ApiResponseAction.MoreDataPresent
                next_min_time = params.get("min_time")
                next_max_time = params.get("max_time")
                next_max_items = params.get("max_items")
                next_page = params.get("page") + 1
            else:
                action = ApiResponseAction.NoMoreDataPresent
                next_min_time = params.get("max_time")
                next_max_time = None
                next_max_items = constants.session_history_page_size
                next_page = 1

            LOG.info(f"Updating SessionHistoryConfig: min_time={next_min_time}, max_time={next_max_time}, max_items={next_max_items}, page={next_page}")
            SessionHistoryConfig(
                min_time=next_min_time,
                max_time=next_max_time,
                max_items=next_max_items,
                page=next_page
            ).save_to_file()

            response.close()
            return ApiResponse(action)
        except Exception as ex:
            LOG.error(f"Exception in session_history script. Exception: {ex}")
            return ApiResponse(ApiResponseAction.ErrorOccurred)

    def resource(self, params):
        LOG.info(f"Fetching resources: host={self.config.host}, app_id={self.config.app_id}, params={params}")
        try:
            """Gets historical data for actions taken on resources managed by the service"""
            api_url = '{}/api/{}/control/reports/resource'.format(
                self.config.host,
                constants.api_version
            )

            self.ensure_signature_in_header(
                api_key=self.config.app_id, secret_key=self.config.signing_key)

            # TODO use context manager 'with' statement to ensure response is closed reliably
            response = requests.get(
                api_url,
                params=params,
                headers=self._headers,
                verify=VERIFY_SSL
            )

            if response.status_code != requests.codes.ok:
                LOG.error(f"MFA server error: {response.text}")
                return ApiResponse(ApiResponseAction.ErrorOccurred)

            response_json = json.loads(response.text)
            page_data = response_json.get('result').get('page')
            page_len = len(page_data)
            LOG.info(f"Total number of resource records in response: {page_len}")

            if len(page_data) > 0:
                for event in page_data:
                    # Remove `json_blob` from the dict
                    json_blob = event.pop("json_blob", {})

                    # TODO - Remove this check once `json_blob` has been renamed to `resource_state`
                    if not json_blob:
                        # Pop a field called resource_state to be forwards compatible
                        json_blob = event.pop("resource_state", {})

                    # Update `json_blob` after converting it into a string
                    # Add new keys `id`, `name`, `user_id` in the base dict
                    # Dump the json_blob/resource_state to `resource_state`
                    event.update({
                        "user_id": json_blob.get("user_id", ""),
                        "username": json_blob.get("username", ""),
                        "resource_state": json.dumps(json_blob)
                    })

                    print("\n", json.dumps(event))

            if page_len == params.get("max_items"):
                action = ApiResponseAction.MoreDataPresent
                next_min_time = params.get("min_time")
                next_max_time = params.get("max_time")
                next_max_items = params.get("max_items")
                next_page = params.get("page") + 1
            else:
                action = ApiResponseAction.NoMoreDataPresent
                next_min_time = params.get("max_time")
                next_max_time = None
                next_max_items = constants.resource_page_size
                next_page = 1

            LOG.info(f"Updating ResourceConfig: min_time={next_min_time}, max_time={next_max_time}, max_items={next_max_items}, page={next_page}")
            ResourceConfig(
                min_time=next_min_time,
                max_time=next_max_time,
                max_items=next_max_items,
                page=next_page
            ).save_to_file()

            response.close()
            return ApiResponse(action)
        except Exception as ex:
            LOG.error(f"Exception in resource script. Exception: {ex}")
            return ApiResponse(ApiResponseAction.ErrorOccurred)
