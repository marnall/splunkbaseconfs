#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""
This module contains all rest calls to Cyberark EPM
"""

import base64
import datetime
import json
import os
import sys
import time
import traceback
import signal
import re

import requests
import requests.adapters

# isort: off
import import_declare_test  # noqa: F401
from cyberark_epm_utils import (
    checkpoint_handler,
    get_cyberark_epm_api_version,
    write_event,
    add_ucc_error_logger,
    add_ucc_ingest_logger,
    time_to_string,
    reformat_string_time,
)
from urllib3.util.retry import Retry
from solnlib.modular_input import event_writer
from constants import *
from kv_checkpointer import Checkpointer


class MaxRetriesExceededError(Exception):
    """Raised when a get_*_events method exhausts its retry budget."""

    pass


class CyberarkConnect:
    """
    This class contains does and handles the API calls for data collection
    """

    def __init__(self, config):
        self.epm_url = config.get("epm_url", None)
        self.auth_type = config.get("auth_type", "basic")
        if self.auth_type == "oauth2":
            self.username = config.get("client_id", None)
            self.password = config.get("client_secret", None)
        else:
            self.username = config.get("username", None)
            self.password = config.get("password", None)
        self.identity_url = config.get("identity_url", None)
        self.app_alias = config.get("app_alias", None)
        self.proxies = config.get("proxies", None)
        self.session_key = config.get("session_key", None)
        self.input_params = config.get("input_params", None)
        if self.input_params:
            self.exc_label = UCC_EXECPTION_EXE_LABEL.format(
                self.input_params.get("input_name").replace("://", ":")
            )
        else:
            self.exc_label = None
        self.ew = event_writer.ClassicEventWriter()
        self.session = None
        self._logger = config.get("logger", None)
        self.token = ""
        self._token_expiry = 0  # Unix timestamp of OAuth2 token exp claim; 0 = no token
        self.manager_url = ""
        self.api_version = get_cyberark_epm_api_version()
        self.nextCursor = "start"
        self.checkpoint_collection = None
        self.events_ingested = False
        self.checkpoint_updated = False
        self.checkpoint_name = None
        self.checkpoint_dict = None
        self.epm_endpoints = {
            "epm_auth": "{}/EPM/API/{}/Auth/EPM/Logon",
            "sets": "{}/EPM/API/{}/Sets",
            "aggregated_events": "{}/EPM/API/{}/Sets/{}/events/aggregations/search",
            "raw_events": "{}/EPM/API/{}/Sets/{}/Events/Search",
            "policy_audit_aggregated_events": "{}/EPM/API/{}/Sets/{}/policyaudits/aggregations/search",
            "policy_audit_raw_events": "{}/EPM/API/{}/Sets/{}/policyaudits/search",
            "policies": "{}/EPM/API/{}/Sets/{}/Policies/Server/Search",
            "policy_details": "{}/EPM/API/{}/Sets/{}/Policies/Server/{}",
            "computers": "{}/EPM/API/{}/Sets/{}/Computers",
            "computer_groups": "{}/EPM/API/{}/Sets/{}/ComputerGroups",
            "admin_audit_logs": "{}/EPM/API/{}/Sets/{}/AdminAudit",
        }
        self.create_requests_session(
            total_retries=2,
            status_forcelist=[
                202,
                204,
                400,
                404,
                405,
                408,
                409,
                429,
                500,
                502,
                503,
                504,
            ],
            allowed_methods=["POST", "GET"],
            backoff_factor=2,
        )

    def exit_gracefully(self, signum, frame):
        """
        This method stores the checkpoint if not done already before terminating the input
        """
        self._logger.info("Execution about to get stopped due to SIGTERM.")
        try:
            if self.events_ingested and not self.checkpoint_updated:
                self._logger.info("Updating the checkpoint before exiting gracefully.")
                self.checkpoint_collection.update(
                    self.checkpoint_name, self.checkpoint_dict
                )
                self._logger.info("Successfully updated the checkpoint before exiting.")
        except Exception as exc:
            msg = "Unable to save checkpoint before SIGTERM termination."
            add_ucc_error_logger(
                self._logger,
                GENERAL_EXCEPTION,
                exc,
                exc_label=self.exc_label,
                msg_before=msg,
            )
        sys.exit(0)

    def create_requests_session(
        self, total_retries, status_forcelist, allowed_methods, backoff_factor
    ):
        """
        This method creates a requests Session and sets retry strategy for the session
        :param total_retries: the number of retries allowed for a request
        :param status_forcelist: list of status codes for which to retry
        :param allowed_methods: the http method for which to apply the retry strategy
        :backoff factor: a factor which induces sleep between retries by the equation:
            {backoff factor} * (2 ** ({number of total retries} - 1))
        """

        try:
            retry_strategy = Retry(
                total=total_retries,
                status_forcelist=status_forcelist,
                allowed_methods=allowed_methods,
                backoff_factor=backoff_factor,
                raise_on_status=False,
            )
            if retry_strategy:
                adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)
                self.session = requests.Session()
                self.session.mount("https://", adapter)
                self.session.mount("http://", adapter)
                self.session.headers.update({"User-Agent": "Splunk-TA-CyberArkEPM/1.0"})
        except Exception as e:
            msg = "Failed to create requests session. Terminating"
            add_ucc_error_logger(
                self._logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=self.exc_label,
                msg_before=msg,
            )

            sys.exit(msg)

    def request_post(self, url, body, headers, params=None):
        """
        This method handles all post requests
        :param url: HTTP URL to make post call
        :param body: Body of the request
        :param headers: Headers of the request
        :param params: Params of the request
        :return: Response of POST call
        """

        response = self.session.post(
            url=url,
            proxies=self.proxies,
            data=body,
            headers=headers,
            params=params,
            verify=True,
            timeout=API_TIME_OUT,
        )
        return response

    def request_get(self, url, headers, params):
        """
        This method handles all get requests
        :param url: HTTP URL to make get call
        :param headers: Headers of the request
        :param params: Parameters of the request
        :return: Response of GET call
        """

        response = self.session.get(
            url=url,
            proxies=self.proxies,
            headers=headers,
            params=params,
            verify=True,
            timeout=API_TIME_OUT,
        )
        return response

    def handle_resp(self, resp):
        """
        This method handles a response based on its status code
        :param resp: The response from an api request
        """

        if resp.status_code == 200:
            return True
        if resp.status_code == 401:
            self._logger.error(
                "EPM API returned 401 (Unauthorized). Re-authenticating."
            )
            self._token_expiry = 0  # Force re-auth regardless of cached expiry
            self.authenticate()
            return False
        if resp.status_code == 403:
            try:
                error_msg = resp.json()[0]["ErrorMessage"]
            except (KeyError, IndexError, TypeError, ValueError):
                error_msg = resp.text
            if "Too many calls" in error_msg:
                self._logger.info(
                    "EPM API rate limit reached: %s. " "Retrying after 10 seconds.",
                    error_msg,
                )
                time.sleep(10)
                return False

        try:
            self._logger.error("Response from EPM Server: " + str(resp.json()))
        except Exception as e:
            msg = "Error while parsing Response JSON"
            add_ucc_error_logger(
                self._logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=self.exc_label,
                msg_before=msg,
            )

        resp.raise_for_status()

    @property
    def headers(self):
        if self.auth_type == "oauth2":
            return {
                "Authorization": "Bearer " + self.token,
                "Content-Type": "application/json",
            }
        return {
            "Authorization": "basic " + self.token,
            "VFUser": self.token,
            "Content-Type": "application/json",
        }

    def authenticate(self, is_request_from_ui=False):
        """
        Dispatches to the correct authentication method based on auth_type.
        """
        if self.auth_type == "oauth2":
            self.oauth2_authentication(is_request_from_ui)
        else:
            self.epm_authentication(is_request_from_ui)

    def _is_token_valid(self):
        """
        Returns True if the current OAuth2 token is present and valid for at least 60 more seconds.
        Reads the exp claim stored from the last successful oauth2_authentication call.
        """
        return bool(self.token) and time.time() < self._token_expiry - 60

    def oauth2_authentication(self, is_request_from_ui=False):
        """
        Authenticates using OAuth2 client_credentials flow via CyberArk Identity.
        Sets self.token to the JWT access token.
        For OAuth2, manager_url is the epm_url directly (no auto-discovery).
        Skips re-authentication if the current token is still valid for more than 60 seconds.
        """
        if not self.identity_url or not self.app_alias:
            msg = "OAuth2 configuration is incomplete: identity_url and app_alias are required."
            self._logger.error(msg)
            if not is_request_from_ui:
                sys.exit(msg)
            else:
                raise Exception(msg)

        if self._is_token_valid():
            self._logger.debug(
                "OAuth2 token still valid (expires in %ds), skipping re-authentication.",
                int(self._token_expiry - time.time()),
            )
            return

        token_url = "{}/oauth2/token/{}".format(
            self.identity_url.rstrip("/"), self.app_alias
        )

        try:
            resp = requests.post(
                url=token_url,
                proxies=self.proxies,
                data={
                    "client_id": self.username,
                    "client_secret": self.password,
                    "grant_type": "client_credentials",
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "Splunk-TA-CyberArkEPM/1.0",
                },
                verify=True,
                timeout=API_TIME_OUT,
                allow_redirects=False,
            )

            if resp.status_code == 200:
                resp_data = resp.json()
                if not resp_data.get("access_token"):
                    raise ValueError(
                        "OAuth2 token response did not contain an access_token."
                    )
                self.token = resp_data["access_token"]
                self.manager_url = self.epm_url
                # Decode JWT exp claim for proactive expiry check
                try:
                    # Validate JWT structure: must have exactly 3 dot-separated parts
                    token_parts = self.token.split(".")
                    if len(token_parts) != 3:
                        self._logger.warning(
                            "Invalid JWT token structure: expected 3 parts, got %d",
                            len(token_parts),
                        )
                        self._token_expiry = 0
                    else:
                        payload_b64 = token_parts[1]
                        payload_b64 += "=" * (4 - len(payload_b64) % 4)
                        claims = json.loads(base64.urlsafe_b64decode(payload_b64))
                        exp = claims.get("exp")
                        self._token_expiry = int(exp) if exp is not None else 0
                except Exception:
                    self._logger.warning(
                        "Failed to decode JWT payload for expiry check, will re-authenticate on next attempt"
                    )
                    # Decode failed — expire immediately (safe fallback)
                    self._token_expiry = 0
                self._logger.info(
                    "Successfully authenticated via OAuth2 to %s", token_url
                )
                return

            self._logger.error(
                "OAuth2 token request failed with status %s", resp.status_code
            )
            resp.raise_for_status()

        except Exception as e:
            msg = "Failed to obtain OAuth2 token from {}.".format(token_url)
            add_ucc_error_logger(self._logger, AUTHENTICATION_ERROR, e, msg_before=msg)
            if not is_request_from_ui:
                sys.exit(
                    "Terminating the modular input as OAuth2 authentication failed"
                )
            else:
                raise Exception(msg)

    def epm_authentication(self, is_request_from_ui=False):
        """
        This function returns token and manager URL which will be used in subsequent API calls
        """

        headers = {"Content-type": "application/json", "Accept": "text/plain"}
        body = {
            "Username": self.username,
            "Password": self.password,
            "ApplicationID": "Splunk",
        }
        url = self.epm_endpoints["epm_auth"].format(self.epm_url, self.api_version)

        try:
            resp = self.request_post(url=url, body=json.dumps(body), headers=headers)

            if resp.status_code in (200, 201):
                resp_data = resp.json()

                # Check if password has expired (API returns 200 but with IsPasswordExpired flag)
                if resp_data.get("IsPasswordExpired", False):
                    msg = "Password has expired for account. Please reset password before using this account."
                    self._logger.error(msg)
                    if not is_request_from_ui:
                        sys.exit(msg)
                    else:
                        raise Exception(msg)

                self.token = resp_data["EPMAuthenticationResult"]
                self.manager_url = resp_data["ManagerURL"]
                return
            try:
                self._logger.error(
                    "Response from EPM Server while authenticating: " + str(resp.json())
                )
            except Exception:
                self._logger.error("Error while parsing Authentication Response JSON")
            resp.raise_for_status()

        except Exception as e:
            msg = "Failed to authenticate to {}.".format(url)
            add_ucc_error_logger(self._logger, AUTHENTICATION_ERROR, e, msg_before=msg)
            if not is_request_from_ui:
                sys.exit(
                    "Terminating the modular input as authentication with EPM server failed"
                )
            else:
                raise Exception(msg)

    def get_sets_list(self):
        """
        This method returns the sets list from the epm server
        :return: The list of set of computers to be managed on EPM instance
        """
        if self.input_params is not None:
            sets_list = self.input_params.get("set_ids", "All").split(",")
            set_objects = []
            uuid_pattern = r"[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}"
            for single_set in sets_list:
                set_parts = single_set.split("|")
                set_id = ""
                set_name = ""
                for s in set_parts:
                    s = s.strip()
                    match = re.search(uuid_pattern, s)
                    if match:
                        set_id = s  # Access by named group
                    else:
                        set_name = set_name + s
                set_objects.append({"Id": set_id, "Name": set_name})
            self._logger.debug(
                "Set_list fetched from input.conf {}".format(set_objects)
            )
            if "All" not in sets_list:
                return set_objects

        params = {"Offset": 0, "Limit": 1000}
        sets_list = []
        error_retries = 0
        try:
            while True:
                resp = self.request_get(
                    url=self.epm_endpoints["sets"].format(
                        self.manager_url, self.api_version
                    ),
                    headers=self.headers,
                    params=params,
                )
                pagination = self.handle_resp(resp)
                if not pagination:
                    error_retries += 1
                    if error_retries >= MAX_RETRIES_ON_ERROR:
                        raise MaxRetriesExceededError(
                            "Max retries ({}) fetching sets list".format(
                                MAX_RETRIES_ON_ERROR
                            )
                        )
                    continue
                error_retries = 0
                if resp.json()["Sets"]:
                    sets_list = sets_list + resp.json()["Sets"]  # merging two lists
                    params["Offset"] = params["Offset"] + params["Limit"]
                    continue

                self._logger.info(
                    "Successfully fetched sets list. Item count is {}".format(
                        len(sets_list)
                    )
                )
                return sets_list
        except Exception as e:
            msg = "Failed to fetch sets list from {}".format(self.manager_url)
            add_ucc_error_logger(
                self._logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=self.exc_label,
                msg_before=msg,
            )
            return []

    def get_inbox_events(self, set_id, checkpoint_data):
        """
        This method returns the list of aggregated events
        :param set_id: unique identifier for the set of devices
        :param checkpoint_data: checkpoint dictionary for the perticular set_id
        :return: The list of aggregated events for the particular set, flag for the next API call and nextCusrsor itself
        """

        start_date = checkpoint_data["start_date"]
        end_date = checkpoint_data["end_date"]
        nextCursor = checkpoint_data["nextCursor"]

        params = {
            "nextCursor": nextCursor,
            "limit": 1000,
        }
        body_json = {}
        if (
            self.input_params.get("application_type")
            and "All" not in self.input_params["application_type"]
        ):
            body_json["applicationType"] = str(self.input_params["application_type"])

        if self.input_params.get("publisher"):
            body_json["publisher"] = str(self.input_params["publisher"])

        if self.input_params.get("justification"):
            body_json["justification"] = str(self.input_params["justification"])

        body = self.prepare_body(start_date, end_date, body_json)
        self._logger.debug(
            f"Body - {body} and nextCursor - '{nextCursor}' to query the EPM server"
        )

        if self.input_params.get("api_type"):
            inbox_events_endpoint = self.epm_endpoints[self.input_params["api_type"]]

        is_alive = 1
        api_type = self.input_params.get("api_type")
        error_retries = 0
        try:
            while True:
                resp = self.request_post(
                    url=inbox_events_endpoint.format(
                        self.manager_url, self.api_version, str(set_id)
                    ),
                    body=json.dumps(body),
                    headers=self.headers,
                    params=params,
                )
                status_of_response = self.handle_resp(resp)

                if not status_of_response:
                    error_retries += 1
                    if error_retries >= MAX_RETRIES_ON_ERROR:
                        self._logger.error(
                            "Reached maximum retries (%d) on non-200 responses "
                            "for %s events. Aborting to prevent stall.",
                            MAX_RETRIES_ON_ERROR,
                            api_type,
                        )
                        raise MaxRetriesExceededError(
                            f"Max retries ({MAX_RETRIES_ON_ERROR}) on {api_type}"
                        )
                    continue

                error_retries = 0
                inbox_events = resp.json()

                inbox_events_list = inbox_events["events"]

                nextCursor = inbox_events["nextCursor"]

                if nextCursor:
                    self._logger.info(
                        "Successfully fetched {} events list. Item count is {}".format(
                            api_type, len(inbox_events_list)
                        )
                    )
                else:
                    is_alive = 0
                    self._logger.info("No data found in the next page.")
                return inbox_events_list, is_alive, nextCursor

        except MaxRetriesExceededError:
            # Re-raise so the broad `except Exception` below doesn't swallow it.
            raise
        except (
            requests.exceptions.ReadTimeout,
            requests.exceptions.ConnectionError,
        ) as e:
            self._logger.warning(
                "EPM API request failed for %s events (%s). "
                "Data collection will resume in the next scheduled run.",
                api_type,
                type(e).__name__,
            )
            raise MaxRetriesExceededError(
                f"API request timed out for {api_type} — likely 100k event volume limit"
            )
        except Exception as e:
            msg = "Failed to fetch {} events from {}".format(api_type, self.manager_url)
            add_ucc_error_logger(
                self._logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=self.exc_label,
                msg_before=msg,
            )
            sys.exit(1)

    def get_policy_audit_events(self, set_id, checkpoint_data):
        """
        This method returns the list of aggregated events
        :param set_id: unique identifier for the set of devices
        :param checkpoint_data: checkpoint dictionary for the perticular set_id
        :return: The list of aggregated events for the particular set, flag for the next API call and nextCusrsor itself
        """
        start_date = checkpoint_data["start_date"]
        end_date = checkpoint_data["end_date"]
        nextCursor = checkpoint_data["nextCursor"]

        params = {
            "nextCursor": nextCursor,
            "limit": 1000,
        }
        body_json = {}

        if self.input_params.get("policy_name"):
            body_json["policyName"] = str(self.input_params["policy_name"])

        if (
            self.input_params.get("application_type")
            and "All" not in self.input_params["application_type"]
        ):
            body_json["applicationType"] = str(self.input_params["application_type"])

        if self.input_params.get("publisher"):
            body_json["publisher"] = str(self.input_params["publisher"])

        if self.input_params.get("justification"):
            body_json["justification"] = str(self.input_params["justification"])

        body = self.prepare_body(start_date, end_date, body_json)
        self._logger.debug(
            f"Body - {body} and nextCursor - '{nextCursor}' to query the EPM server"
        )

        if self.input_params.get("api_type"):
            policy_audit_events_endpoint = self.epm_endpoints[
                "policy_audit_{}".format(self.input_params["api_type"])
            ]

        is_alive = 1
        api_type = self.input_params.get("api_type")
        error_retries = 0
        try:
            while True:
                resp = self.request_post(
                    url=policy_audit_events_endpoint.format(
                        self.manager_url, self.api_version, str(set_id)
                    ),
                    body=json.dumps(body),
                    headers=self.headers,
                    params=params,
                )
                status_of_response = self.handle_resp(resp)

                if not status_of_response:
                    error_retries += 1
                    if error_retries >= MAX_RETRIES_ON_ERROR:
                        self._logger.error(
                            "Reached maximum retries (%d) on non-200 responses "
                            "for %s events. Aborting to prevent stall.",
                            MAX_RETRIES_ON_ERROR,
                            api_type,
                        )
                        raise MaxRetriesExceededError(
                            f"Max retries ({MAX_RETRIES_ON_ERROR}) on {api_type}"
                        )
                    continue

                error_retries = 0
                policy_audit_events = resp.json()

                policy_audit_events_list = policy_audit_events["events"]

                nextCursor = policy_audit_events["nextCursor"]

                if nextCursor:
                    self._logger.info(
                        "Successfully fetched {} events list. Item count is {}".format(
                            api_type, len(policy_audit_events_list)
                        )
                    )
                    return policy_audit_events_list, is_alive, nextCursor
                else:
                    is_alive = 0
                    self._logger.info("No data found in the next page.")
                    return policy_audit_events_list, is_alive, nextCursor

        except MaxRetriesExceededError:
            # Re-raise so the broad `except Exception` below doesn't swallow it.
            raise
        except (
            requests.exceptions.ReadTimeout,
            requests.exceptions.ConnectionError,
        ) as e:
            self._logger.warning(
                "EPM API request failed for %s events (%s). "
                "Data collection will resume in the next scheduled run.",
                api_type,
                type(e).__name__,
            )
            raise MaxRetriesExceededError(
                f"API request timed out for {api_type} — likely 100k event volume limit"
            )
        except Exception as e:
            msg = "Failed to fetch {} events from {}".format(api_type, self.manager_url)
            add_ucc_error_logger(
                self._logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=self.exc_label,
                msg_before=msg,
            )
            sys.exit(1)

    def prepare_body(self, start_date, end_date, body_json):
        filter_operation = f"(arrivalTime between {start_date}, {end_date})"
        if body_json.get("justification"):
            filter_operation = (
                filter_operation
                + f' AND (justification IS {body_json.get("justification")})'
            )
        if body_json.get("publisher"):
            filter_operation = (
                filter_operation
                + f' AND (publisher CONTAINS "{body_json.get("publisher")}")'
            )
        if body_json.get("policyName"):
            filter_operation = (
                filter_operation
                + f' AND (policyName CONTAINS "{body_json.get("policyName")}")'
            )
        if body_json.get("applicationType"):
            filter_operation = (
                filter_operation
                + f' AND (applicationType IN {body_json.get("applicationType")})'
            )
        prepared_body = {"filter": filter_operation}
        return prepared_body

    def _write_events(self, events_list, set_id=None):
        """
        This method ingest given list of events into splunk
        """

        ew_event_list = list()
        calculated_source = "{}:{}".format(
            self.input_params["input_name"].replace("://", ":"),
            self.input_params["account_name"],
        )
        calculated_host = (
            self.manager_url.split("://")[1]
            if "https://" in self.manager_url
            else self.manager_url
        )
        for event in events_list:
            if set_id:
                event["Set_id"] = set_id
            ew_event_list.append(
                self.ew.create_event(
                    data=json.dumps(event),
                    sourcetype=self.input_params["sourcetype"],
                    source=calculated_source,
                    host=calculated_host,
                    index=self.input_params["index"],
                )
            )
        self.ew.write_events(ew_event_list)

    def collect_data(self):
        """
        This method collects data for a particular category of events.
        Execution is time-bounded by MAX_EXECUTION_TIME to prevent a single
        run from monopolising the process for hours/days when there is a
        large volume of data to paginate through.  The checkpoint is
        persisted after every page, so the next scheduled run resumes
        exactly where this one stopped.
        """
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
        # for windows machine
        if os.name == "nt":
            signal.signal(signal.SIGBREAK, self.exit_gracefully)  # pylint:disable=E1101

        execution_start_time = time.time()

        self.authenticate()
        sets_list = self.get_sets_list()

        default_start_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=6)
        start_date = self.input_params.get("start_date") or default_start_time
        collection_name = self.input_params.get("collection_name")
        self.checkpoint_name = self.input_params["input_name"].replace("://", "_")
        try:
            for each_set in sets_list:
                set_id = each_set["Id"]
                (
                    checkpoint_success,
                    self.checkpoint_collection,
                    self.checkpoint_dict,
                ) = checkpoint_handler(
                    self._logger,
                    self.session_key,
                    set_id,
                    self.checkpoint_name,
                    start_date,
                    collection_name,
                )
                input_type = self.input_params["input_name"].split("://")[0]
                is_alive = True
                if checkpoint_success:
                    while is_alive:
                        self.events_ingested = False
                        self.checkpoint_updated = False
                        if input_type == "inbox_events":
                            (
                                events_list,
                                is_alive,
                                nextCursor,
                            ) = self.get_inbox_events(
                                set_id, self.checkpoint_dict[set_id]
                            )
                        else:
                            (
                                events_list,
                                is_alive,
                                nextCursor,
                            ) = self.get_policy_audit_events(
                                set_id, self.checkpoint_dict[set_id]
                            )

                        if is_alive:
                            self.checkpoint_dict[set_id]["nextCursor"] = nextCursor
                            log_message = "nextCursor found and checkpoint updated for the next API call."
                        else:
                            temp = self.checkpoint_dict[set_id]["end_date"]
                            self.checkpoint_dict[set_id]["nextCursor"] = "start"
                            self.checkpoint_dict[set_id]["start_date"] = temp
                            self.checkpoint_dict[set_id]["end_date"] = None
                            log_message = "No data found in next page hence updated nextCursor value start for the next interval."

                        self._write_events(events_list, set_id)
                        self.events_ingested = True

                        add_ucc_ingest_logger(
                            self._logger, self.input_params, len(events_list)
                        )
                        self.checkpoint_collection.update(
                            self.checkpoint_name, self.checkpoint_dict
                        )
                        self.checkpoint_updated = True
                        self._logger.info(log_message)

                        # Guard: stop paginating if this execution has been
                        # running longer than the allowed maximum.  The
                        # checkpoint was already saved above so the next
                        # scheduled run will continue from this cursor.
                        elapsed = time.time() - execution_start_time
                        if is_alive and elapsed > MAX_EXECUTION_TIME:
                            self._logger.info(
                                "Maximum execution time of %d seconds exceeded "
                                "(elapsed: %d seconds). Checkpoint saved — "
                                "remaining data will be collected in the next "
                                "scheduled run.",
                                MAX_EXECUTION_TIME,
                                int(elapsed),
                            )
                            return
        except MaxRetriesExceededError:
            self._logger.error(
                "Stopping data collection for input '%s' due to repeated "
                "API failures. Checkpoint preserved — next run will retry "
                "from the same position.",
                self.input_params["input_name"],
            )
        except Exception as e:
            msg = "Error in data collection for input: {}".format(
                self.input_params["input_name"]
            )
            add_ucc_error_logger(
                self._logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=self.exc_label,
                msg_before=msg,
            )
            sys.exit(1)

    def collect_admin_audit_logs(self):
        """
        This method collects data for the admin audit logs
        """
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
        # for windows machine
        if os.name == "nt":
            signal.signal(signal.SIGBREAK, self.exit_gracefully)  # pylint:disable=E1101

        self.authenticate()
        sets_list = self.get_sets_list()

        start_date = self.input_params.get("start_date")
        if not start_date:
            start_date = datetime.datetime.utcnow() - datetime.timedelta(minutes=6)
        collection_name = self.input_params.get("collection_name")
        self.checkpoint_name = self.input_params["input_name"].replace("://", "_")
        page_limit = 500
        try:
            for each_set in sets_list:
                set_id = each_set["Id"]
                (
                    checkpoint_success,
                    self.checkpoint_collection,
                    self.checkpoint_dict,
                ) = checkpoint_handler(
                    self._logger,
                    self.session_key,
                    set_id,
                    self.checkpoint_name,
                    start_date,
                    collection_name,
                )
                is_alive = True
                total_events = 0
                if checkpoint_success:
                    self.checkpoint_dict[set_id]["nextCursor"] = (
                        0
                        if self.checkpoint_dict[set_id]["nextCursor"] == "start"
                        else int(self.checkpoint_dict[set_id]["nextCursor"])
                    )
                    while is_alive:
                        self.events_ingested = False
                        self.checkpoint_updated = False
                        events_list, end_date = self.get_admin_audit_logs(
                            set_id, self.checkpoint_dict[set_id], page_limit
                        )
                        events_count = len(events_list)
                        if events_count < page_limit:
                            self.checkpoint_dict[set_id]["start_date"] = end_date
                            self.checkpoint_dict[set_id]["end_date"] = None
                            self.checkpoint_dict[set_id]["nextCursor"] = 0
                            is_alive = False
                        else:
                            self.checkpoint_dict[set_id]["nextCursor"] += page_limit

                        self._write_events(events_list, set_id)

                        self.events_ingested = True
                        total_events += events_count
                        add_ucc_ingest_logger(
                            self._logger,
                            self.input_params,
                            events_count,
                        )
                        self.checkpoint_collection.update(
                            self.checkpoint_name, self.checkpoint_dict
                        )
                        self.checkpoint_updated = True

                    self._logger.info(
                        "Successfully ingested total {} events for set {}".format(
                            total_events, each_set["Name"]
                        )
                    )

        except MaxRetriesExceededError:
            self._logger.error(
                "Stopping admin audit data collection for input '%s' due to "
                "repeated API failures. Checkpoint preserved — next run will "
                "retry from the same position.",
                self.input_params["input_name"],
            )
        except Exception as e:
            msg = "Error in data collection for input: {}".format(
                self.input_params["input_name"]
            )
            add_ucc_error_logger(
                self._logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=self.exc_label,
                msg_before=msg,
            )
            sys.exit(1)

    def get_admin_audit_logs(self, set_id, checkpoint_data, page_limit):
        """
        This method returns the list of admin audit logs
        :param set_id: unique identifier for the set of devices
        :param checkpoint_data: checkpoint dictionary for the perticular set_id
        :return: The list of admin audit logs for the particular set and end_date
        """
        start_date = checkpoint_data["start_date"]
        end_date = checkpoint_data["end_date"]
        offset = checkpoint_data["nextCursor"]
        params = {
            "offset": offset,
            "limit": page_limit,
            "DateFrom": start_date,
            "DateTo": end_date,
        }
        error_retries = 0
        try:
            while True:
                now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                resp = self.request_get(
                    url=self.epm_endpoints["admin_audit_logs"].format(
                        self.manager_url, self.api_version, str(set_id)
                    ),
                    headers=self.headers,
                    params=params,
                )
                status_of_response = self.handle_resp(resp)

                if not status_of_response:
                    error_retries += 1
                    if error_retries >= MAX_RETRIES_ON_ERROR:
                        self._logger.error(
                            "Reached maximum retries (%d) on non-200 responses "
                            "for admin_audit_logs. Aborting to prevent stall.",
                            MAX_RETRIES_ON_ERROR,
                        )
                        raise MaxRetriesExceededError(
                            f"Max retries ({MAX_RETRIES_ON_ERROR}) on admin_audit_logs"
                        )
                    continue

                error_retries = 0

                admin_audits = resp.json()

                admin_audits_list = admin_audits["AdminAudits"]

                return admin_audits_list, now

        except (
            requests.exceptions.ReadTimeout,
            requests.exceptions.ConnectionError,
        ) as e:
            self._logger.info(
                "EPM API request timed out for admin audit logs "
                "(possible 100k volume rate limit): %s. "
                "Data collection will resume in the next scheduled run.",
                type(e).__name__,
            )
            raise MaxRetriesExceededError(
                "API request timed out for admin_audit — likely 100k event volume limit"
            )
        except Exception as e:
            msg = "Failed to fetch Admin audit logs from {}".format(self.manager_url)
            add_ucc_error_logger(
                self._logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=self.exc_label,
                msg_before=msg,
            )
            sys.exit(1)

    def collect_policies_and_computers(
        self, collect_data_for, collect_policy_details, event_writer
    ):
        """
        This method collects data for a policies, policy details, computers and computer groups selectively
        :param collect_data_for: set of options to collect data for
        :param event_writer: Splunk EventWriter object used to index data
        """

        self.authenticate()
        sets_list = self.get_sets_list()

        for each_set in sets_list:
            set_id = each_set["Id"]

            if "policies" in collect_data_for:
                policy_list = self.get_policies(set_id)
                if collect_policy_details == "1":
                    self._logger.debug("Proceeding to fetch policy details.")
                    for index, policy in enumerate(policy_list):
                        policy_details = self.get_policy_details(
                            set_id, policy["PolicyId"]
                        )
                        if policy_details.get("ErrorMessage"):
                            self._logger.warning(
                                "Error while fetching Policy Details for PolicyId : {}, continuing with Policy Event".format(
                                    policy["PolicyId"]
                                )
                            )
                            policy_list[index] = policy
                        else:

                            policy_list[index] = policy_details

                for policy in policy_list:
                    _ = write_event(
                        self._logger,
                        event_writer,
                        policy,
                        "cyberark:epm:policies",
                        self.input_params,
                        self.manager_url,
                        set_id,
                    )
                add_ucc_ingest_logger(
                    self._logger,
                    self.input_params,
                    len(policy_list),
                    special_sourcetype="cyberark:epm:policies",
                )

            if "computers" in collect_data_for:
                computer_list = self.get_computers(set_id)
                for computer in computer_list:
                    _ = write_event(
                        self._logger,
                        event_writer,
                        computer,
                        "cyberark:epm:computers",
                        self.input_params,
                        self.manager_url,
                        set_id,
                    )
                add_ucc_ingest_logger(
                    self._logger,
                    self.input_params,
                    len(computer_list),
                    special_sourcetype="cyberark:epm:computers",
                )

            if "computer_groups" in collect_data_for:
                computer_group_list = self.get_computer_groups(set_id)
                for computer_group in computer_group_list:
                    _ = write_event(
                        self._logger,
                        event_writer,
                        computer_group,
                        "cyberark:epm:computer:groups",
                        self.input_params,
                        self.manager_url,
                        set_id,
                    )
                add_ucc_ingest_logger(
                    self._logger,
                    self.input_params,
                    len(computer_group_list),
                    special_sourcetype="cyberark:epm:computer:groups",
                )

    def get_policies(self, set_id):
        """
        :param set_id: unique identifier for the set of devices
        :return policy_list: list of policies
        """

        params = {"Offset": 0, "Limit": 100}
        policy_list = []
        try:
            while True:
                resp = self.request_post(
                    url=self.epm_endpoints["policies"].format(
                        self.manager_url, self.api_version, str(set_id)
                    ),
                    body=None,
                    headers=self.headers,
                    params=params,
                )
                pagination = self.handle_resp(resp)
                if not pagination:
                    continue
                if resp.json()["Policies"]:
                    policy_list = (
                        policy_list + resp.json()["Policies"]
                    )  # merging two lists
                    params["Offset"] = params["Offset"] + params["Limit"]
                    continue
                self._logger.info(
                    "Successfully fetched policy list. Item count is {}".format(
                        len(policy_list)
                    )
                )
                return policy_list
        except Exception as e:
            msg = "Failed to fetch policies from {}".format(self.manager_url)
            add_ucc_error_logger(
                self._logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=self.exc_label,
                msg_before=msg,
            )
            return []

    def get_policy_details(self, set_id, policy_id):
        """
        :param set_id: unique identifier for the set of devices
        :param policy_id: unique identifier for the policy
        :return : dictionary containing policy details
        """

        try:
            while True:
                resp = self.request_get(
                    self.epm_endpoints["policy_details"].format(
                        self.manager_url, self.api_version, str(set_id), policy_id
                    ),
                    headers=self.headers,
                    params=None,
                )
                if resp.status_code == 400:
                    return resp.json()[0]
                pagination = self.handle_resp(resp)
                if not pagination:
                    continue
                self._logger.debug("Successfully fetched policy details")
                return resp.json()
        except Exception as e:
            msg = "Failed to get policy details from {}".format(self.manager_url)
            add_ucc_error_logger(
                self._logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=self.exc_label,
                msg_before=msg,
            )
            return {}

    def get_computers(self, set_id):
        """
        :param set_id: unique identifier for the set of devices
        :return computer_list: list of computers
        """

        params = {"Offset": 0, "Limit": 100}
        computer_list = []
        try:
            while True:
                resp = self.request_get(
                    self.epm_endpoints["computers"].format(
                        self.manager_url, self.api_version, str(set_id)
                    ),
                    headers=self.headers,
                    params=params,
                )

                pagination = self.handle_resp(resp)

                if not pagination:
                    continue
                if resp.json()["Computers"]:
                    computer_list = (
                        computer_list + resp.json()["Computers"]
                    )  # merging two lists
                    params["Offset"] = params["Offset"] + params["Limit"]
                    continue
                self._logger.info(
                    "Successfully fetched computer list. Item count is {}".format(
                        len(computer_list)
                    )
                )

                return computer_list
        except Exception as e:
            msg = "Failed to get computers from {}".format(self.manager_url)
            add_ucc_error_logger(
                self._logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=self.exc_label,
                msg_before=msg,
            )
            return []

    def get_computer_groups(self, set_id):
        """
        :param set_id: unique identifier for the set of devices
        :return : list containing dictionaries of computer groups
        """

        try:
            while True:
                resp = self.request_get(
                    self.epm_endpoints["computer_groups"].format(
                        self.manager_url, self.api_version, str(set_id)
                    ),
                    headers=self.headers,
                    params=None,
                )

                pagination = self.handle_resp(resp)
                if not pagination:
                    continue
                self._logger.info(
                    "Successfully fetched computer group list. Item count is {}".format(
                        len(resp.json()["ComputerGroups"])
                    )
                )
                return resp.json()["ComputerGroups"]
        except Exception as e:
            msg = "Failed to get computers groups from {}".format(self.manager_url)
            add_ucc_error_logger(
                self._logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=self.exc_label,
                msg_before=msg,
            )
            return []


class AccountAdminLogs(CyberarkConnect):
    def __init__(self, config):
        super(AccountAdminLogs, self).__init__(config)
        self.authenticate()
        self._account_admin_url = self.manager_url + "/EPM/API/Account/AdminAudit"
        self._page_limit = PAGE_LIMIT
        self._time_format = "%Y-%m-%dT%H:%M:%SZ"
        self._collection_name = self.input_params.get("collection_name")
        self._checkpoint_name = self.input_params["input_name"].replace("://", "_")
        self._cache = {}
        self._checkpointer = None
        self._initialise_checkpointer()
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
        # Windows machine
        if os.name == "nt":
            signal.signal(signal.SIGBREAK, self.exit_gracefully)  # pylint:disable=E1101

    def exit_gracefully(self, signum, frame):
        """
        Exit gracefully in case of sudden exit/input disabled
        """
        try:
            self._logger.info("Execution about to get stopped due to SIGTERM.")
            self._save_checkpoint()
        except Exception as exc:
            msg = "Unable to save checkpoint before SIGTERM termination."
            add_ucc_error_logger(
                self._logger,
                GENERAL_EXCEPTION,
                exc,
                exc_label=self.exc_label,
                msg_before=msg,
            )
            sys.exit(1)

    def _initialise_checkpointer(self):
        """
        Initialise KVStore collection and fetch checkpoint details
        """
        try:
            self._checkpointer = Checkpointer(self._collection_name, self.session_key)
            # get returns dictionary or None(In case of any exception)
            # or raise exception if 404 with Get checkpoint failed error
            self._cache = self._checkpointer.get(self._checkpoint_name) or {}
            self._logger.info(f"Checkpoint details - {self._cache}")
        except Exception as e:
            add_ucc_error_logger(
                self._logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=self.exc_label,
                msg_before="Error in fetching checkpoint details. Exiting Input",
            )
            sys.exit(1)

    def _save_checkpoint(self):
        """
        Save current state of _cache in KVStore
        """
        self._logger.info(f"Saving checkpoint info: {self._cache}")
        self._checkpointer.update(self._checkpoint_name, self._cache)
        self._logger.debug(f"Successfully updated checkpoint info")

    def _get_default_start_date(self):
        """
        Calculate default start_date, which would be 6 minutes less than utcnow()
        """
        default_start_date = datetime.datetime.now(
            tz=datetime.timezone.utc
        ) - datetime.timedelta(minutes=6)
        return time_to_string(self._time_format, default_start_date)

    def collect_account_admin_audit_logs(self):
        """
        Collect account admin audit logs data
        """
        start_date = (
            self._cache.get("start_date")
            or self.input_params.get("start_date")
            or self._get_default_start_date()
        )
        try:
            for events in self._get_account_admin_audit_logs(start_date):
                self._logger.info(f"Events recieved - {len(events)}")
                if not events:
                    self._logger.info("No events found in the response; skipping")
                    continue
                next_start_date = reformat_string_time(
                    self._time_format, events[-1]["EventTime"]
                )
                self._write_events(events)
                add_ucc_ingest_logger(
                    self._logger,
                    self.input_params,
                    len(events),
                )
                # update start_date in cache
                self._cache["start_date"] = next_start_date
                self._logger.info(
                    f"Updating temp cache with time: {next_start_date}, Data Ingested: {len(events)}"
                )
        except Exception as e:
            add_ucc_error_logger(
                self._logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=self.exc_label,
                msg_before="Exception while data ingestion",
            )
        self._save_checkpoint()

    def _get_account_admin_audit_logs(self, start_date):
        """
        Make API calls to fetch logs
        """
        offset = 0
        while True:
            params = {
                "DateFrom": start_date,
                "limit": self._page_limit,
                "offset": offset,
            }
            self._logger.info(
                f"Making API call - {self._account_admin_url} with params - {params}"
            )
            resp = self.request_get(
                url=self._account_admin_url,
                headers=self.headers,
                params=params,
            )
            if not self.handle_resp(resp):
                continue
            data = resp.json()
            admin_audits = data["AdminAudits"]
            yield admin_audits
            if len(admin_audits) < self._page_limit:
                break
            else:
                offset += len(admin_audits)
