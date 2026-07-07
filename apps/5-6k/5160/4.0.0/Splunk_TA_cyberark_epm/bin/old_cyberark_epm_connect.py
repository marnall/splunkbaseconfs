#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""
This module contains all rest calls to Cyberark EPM
"""

import datetime
import json
import sys
import time
import traceback

import requests

# isort: off
import import_declare_test  # noqa: F401
from old_cyberark_epm_utils import (
    checkpoint_handler,
    get_cyberark_epm_api_version,
    write_event,
)
from cyberark_epm_utils import add_ucc_error_logger, add_ucc_ingest_logger
from urllib3.util.retry import Retry
from constants import *


class CyberarkConnect:
    """
    This class contains does and handles the API calls for data collection
    """

    def __init__(self, config):

        self.epm_url = config["epm_url"]
        self.username = config["username"]
        self.password = config["password"]
        self.category = config["category"]
        self.proxies = config["proxies"]
        self.session_key = config["session_key"]
        self.input_params = config["input_params"]
        self._logger = config["logger"]
        self.token = ""
        self.exc_label = UCC_EXECPTION_EXE_LABEL.format(
            self.input_params.get("input_name").replace("://", ":")
        )
        self.manager_url = ""
        self.api_version = get_cyberark_epm_api_version()
        self.start_time = ""
        self.current_time = datetime.datetime.strftime(
            datetime.datetime.utcnow(), "%Y-%m-%dT%H:%M:%SZ"
        )
        self.epm_endpoints = {
            "epm_auth": "{}/EPM/API/{}/Auth/EPM/Logon",
            "sets": "{}/EPM/API/{}/Sets",
            "aggregated_events": "{}/EPM/API/{}/Sets/{}/Events/{}",
            "policies": "{}/EPM/API/{}/Sets/{}/Policies",
            "policy_details": "{}/EPM/API/{}/Sets/{}/Policies/{}",
            "computers": "{}/EPM/API/{}/Sets/{}/Computers",
            "computer_groups": "{}/EPM/API/{}/Sets/{}/ComputerGroups",
        }
        self.create_requests_session(
            total_retries=2,
            status_forcelist=[
                202,
                204,
                400,
                401,
                403,
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
            method_whitelist=["POST, GET"],
            backoff_factor=2,
        )

    def create_requests_session(
        self, total_retries, status_forcelist, method_whitelist, backoff_factor
    ):
        """
        This method creates a requests Session and sets retry strategy for the session
        :param total_retries: the number of retries allowed for a request
        :param status_forcelist: list of status codes for which to retry
        :param method_whitelist: the http method for which to apply the retry strategy
        :backoff factor: a factor which induces sleep between retries by the equation:
            {backoff factor} * (2 ** ({number of total retries} - 1))
        """

        try:
            retry_strategy = Retry(
                total=total_retries,
                status_forcelist=status_forcelist,
                method_whitelist=method_whitelist,
                backoff_factor=backoff_factor,
            )
            if retry_strategy:
                adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)
                self.session = requests.Session()
                self.session.mount("https://", adapter)
                self.session.mount("http://", adapter)
        except Exception as e:
            msg = "Failed to create requests session."
            add_ucc_error_logger(
                self._logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=self.exc_label,
                msg_before=msg,
            )
            sys.exit("Failed to create requests session. Terminating.")

    def request_post(self, url, body, headers):
        """
        This method handles all post requests
        :param url: HTTP URL to make post call
        :param body: Body of the request
        :param headers: Headers of the request
        :return: Response of POST call
        """

        response = self.session.post(
            url=url, proxies=self.proxies, data=body, headers=headers, verify=True
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
            url=url, proxies=self.proxies, headers=headers, params=params, verify=True
        )
        return response

    def handle_resp(self, resp):
        """
        This method handles a response based on its status code
        :param resp: The response from an api request
        """

        if resp.status_code == 200:
            return True
        if (
            resp.status_code == 401
            and resp.json()[0]["ErrorMessage"]
            == "Your session has expired and your user has been disconnected."
        ):
            self._logger.error("EPM Token expired. Getting new token.")
            self.epm_authentication()
            return False
        if resp.status_code == 403:
            error_msg = resp.json()[0]["ErrorMessage"]
            if "Too many calls" in error_msg:
                error_msg = error_msg.split(" ")
                max_api_calls, time_period = error_msg[9], error_msg[4]
                self._logger.debug(
                    "Maximum limit ({}) for number of API calls exceeded. Going into sleep for {} minute(s)".format(
                        max_api_calls, time_period
                    )
                )
                time.sleep(int(time_period) * 60)
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

    def epm_authentication(self):
        """
        This function returns token and manager URL which will be used in subsequent API calls
        :param epm_url: CyberArk EPM Dispatcher URL
        :param username: Usename for CyberArk EPM
        :param password: Password for CyberArk EPM
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
                    sys.exit(msg)

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
            sys.exit(
                "Terminating the modular input as authentication with EPM server failed"
            )

    def get_sets_list(self):
        """
        This method returns the sets list from the epm server
        :return: The list of set of computers to be managed on EPM instance
        """
        headers = {
            "Authorization": "basic" + self.token,
            "VFUser": self.token,
            "Content-Type": "application/json",
        }
        params = {"Offset": 0, "Limit": 1000}
        sets_list = []
        try:
            while True:
                resp = self.request_get(
                    url=self.epm_endpoints["sets"].format(
                        self.manager_url, self.api_version
                    ),
                    headers=headers,
                    params=params,
                )
                pagination = self.handle_resp(resp)
                if not pagination:
                    continue
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

    def get_aggregated_events(self, set_id):
        """
        This method returns the list of aggregated events
        :param set_id: unique identifier for the set of devices
        :return: The list of aggregated events for the particular set
        """

        headers = {
            "Authorization": "basic" + self.token,
            "VFUser": self.token,
            "Content-Type": "application/json",
        }
        params = {
            "Offset": 0,
            "Limit": 100,
            "DateFrom": self.start_time,
            "DateTo": self.current_time,
        }
        if "publisher" in self.input_params.keys():
            params["Publisher"] = self.input_params["publisher"]

        if "justification" in self.input_params.keys():
            params["Justification"] = self.input_params["justification"]

        if "application_type" in self.input_params.keys():
            if "All" in self.input_params["application_type"]:
                params["ApplicationType"] = "All"
            else:
                params["ApplicationType"] = self.input_params["application_type"]

        if "policy_name" in self.input_params.keys():
            params["PolicyName"] = self.input_params["policy_name"]

        aggr_events_list = []
        try:
            while True:
                resp = self.request_get(
                    url=self.epm_endpoints["aggregated_events"].format(
                        self.manager_url, self.api_version, str(set_id), self.category
                    ),
                    headers=headers,
                    params=params,
                )

                pagination = self.handle_resp(resp)

                if not pagination:
                    continue
                if resp.json()["Events"]:
                    aggr_events_list = (
                        aggr_events_list + resp.json()["Events"]
                    )  # merging two lists
                    params["Offset"] = params["Offset"] + params["Limit"]
                    continue

                self._logger.info(
                    "Successfully fetched aggregated events list. Item count is {}".format(
                        len(aggr_events_list)
                    )
                )
                return aggr_events_list
        except Exception as e:
            msg = "Failed to fetch aggregated events from {}".format(self.manager_url)
            add_ucc_error_logger(
                self._logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=self.exc_label,
                msg_before=msg,
            )
            return []

    def collect_data(self, event_writer):
        """
        This method collects data for a particular category of events
        :param event_writer: Splunk EventWriter object used to index data
        """

        self.epm_authentication()

        sets_list = self.get_sets_list()
        for each_set in sets_list:
            checkpoint_name = self.input_params["input_name"].replace("://", "_")
            set_id = each_set["Id"]
            (
                checkpoint_success,
                checkpoint_collection,
                query_start_date,
            ) = checkpoint_handler(
                self._logger, self.session_key, set_id, checkpoint_name
            )
            if checkpoint_success:
                checkpoint_dict = checkpoint_collection.get(checkpoint_name)
                self.start_time = query_start_date
                aggregated_events_list = self.get_aggregated_events(set_id)

                for index in range(len(aggregated_events_list) - 1, -1, -1):
                    aggregated_event = aggregated_events_list[index]
                    event_written = write_event(
                        self._logger,
                        event_writer,
                        aggregated_event,
                        self.input_params["sourcetype"],
                        self.input_params,
                        self.manager_url,
                    )
                    if not event_written:
                        break
                    add_ucc_ingest_logger(self._logger, self.input_params, 1)
                    checkpoint_dict[set_id] = (
                        (aggregated_event["LastEventDate"][:19] + "Z")
                        if index != 0
                        else str(self.current_time)
                    )
                    checkpoint_collection.update(checkpoint_name, checkpoint_dict)

    def collect_policies_and_computers(
        self, collect_data_for, collect_policy_details, event_writer
    ):
        """
        This method collects data for a policies, policy details, computers and computer groups selectively
        :param collect_data_for: set of options to collect data for
        :param event_writer: Splunk EventWriter object used to index data
        """

        self.epm_authentication()
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
                        policy_details["PolicyId"] = policy["PolicyId"]
                        policy_details["Description"] = policy["Description"]
                        policy_details["Active"] = policy["Active"]
                        policy_details["CreateTime"] = policy["CreateTime"]
                        policy_details["UpdateTime"] = policy["UpdateTime"]
                        policy_details["Priority"] = policy["Priority"]
                        policy_list[index] = policy_details

                for policy in policy_list:
                    _ = write_event(
                        self._logger,
                        event_writer,
                        policy,
                        "cyberark:epm:policies",
                        self.input_params,
                        self.manager_url,
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

        headers = {
            "Authorization": "basic" + self.token,
            "VFUser": self.token,
            "Content-Type": "application/json",
        }
        params = {"Offset": 0, "Limit": 100}
        policy_list = []
        try:
            while True:
                resp = self.request_get(
                    url=self.epm_endpoints["policies"].format(
                        self.manager_url, self.api_version, str(set_id)
                    ),
                    headers=headers,
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

        headers = {
            "Authorization": "basic" + self.token,
            "VFUser": self.token,
            "Content-Type": "application/json",
        }
        try:
            while True:
                resp = self.request_get(
                    self.epm_endpoints["policy_details"].format(
                        self.manager_url, self.api_version, str(set_id), policy_id
                    ),
                    headers=headers,
                    params=None,
                )
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

        headers = {
            "Authorization": "basic" + self.token,
            "VFUser": self.token,
            "Content-Type": "application/json",
        }
        params = {"Offset": 0, "Limit": 100}
        computer_list = []
        try:
            while True:
                resp = self.request_get(
                    self.epm_endpoints["computers"].format(
                        self.manager_url, self.api_version, str(set_id)
                    ),
                    headers=headers,
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

        headers = {
            "Authorization": "basic" + self.token,
            "VFUser": self.token,
            "Content-Type": "application/json",
        }
        try:
            while True:
                resp = self.request_get(
                    self.epm_endpoints["computer_groups"].format(
                        self.manager_url, self.api_version, str(set_id)
                    ),
                    headers=headers,
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
