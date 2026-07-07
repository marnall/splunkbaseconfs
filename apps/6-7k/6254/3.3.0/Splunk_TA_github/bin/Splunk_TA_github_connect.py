#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""
This module contains all rest calls to GitHub
"""

import traceback

import requests
import signal

# isort: off
import import_declare_test  # noqa: F401
import os  # noqa: F401
import os.path as op
from Splunk_TA_github_utils import write_event, checkpoint_handler
from urllib.parse import urlparse, parse_qs
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from splunktaucclib.rest_handler.error import RestError
from solnlib.modular_input import checkpointer, event_writer
from solnlib import log
from Splunk_TA_github_alert_utils import AlertUtils
import Splunk_TA_github_consts as constants
import sys
import json

APP_NAME = __file__.split(op.sep)[-3]

CHECKPOINTER = "Splunk_TA_github_checkpointer"

PER_PAGE = 100
DEFAULT_ALERT_LAST_UPDATED_AT = "1970-01-01T00:00:00.000Z"
ALERT_START_DATE_CHECKPOINT_KEY = "start_date"

sourcetype_dict = {
    "code_scanning_alerts": constants.GITHUB_CS_ALERT_SOURCE_TYPE,
    "dependabot_alerts": constants.GITHUB_DB_ALERT_SOURCE_TYPE,
    "secret_scanning_alerts": constants.GITHUB_SS_ALERT_SOURCE_TYPE,
}


class GitHubConnect:
    """
    This class contains does and handles the API calls for data collection
    """

    def __init__(self, config):

        self.security_token = config["security_token"]
        self.proxies = config["proxies"]
        self.session_key = config["session_key"]
        self.input_params = config["input_params"]
        self._logger = config["logger"]
        self.account_name = config["account_name"]
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(self.security_token),
        }
        self.create_requests_session(
            total_retries=3,
            status_forcelist=[403, 404, 429, 503],
            method_whitelist=["POST", "GET"],
            backoff_factor=1,
        )
        self.checkpoint_dict = None
        self.checkpoint_updated = False
        self.checkpoint_key = None
        self.events_ingested = 0
        self.license_usage_source = ":".join(
            [self.input_params["name"].replace("://", ":"), self.account_name]
        )

    @staticmethod
    def _format_alert_start_date(start_date):
        """
        Format the alerts start date for checkpoint comparison.
        """
        if not start_date:
            return None

        formatted_start = start_date[:-1] if start_date.endswith("Z") else start_date
        if "." not in formatted_start:
            formatted_start = "{}.000".format(formatted_start)
        return "{}Z".format(formatted_start)

    @staticmethod
    def _get_applied_alert_start_date(checkpoint_value):
        """
        Return the start date already applied to the alerts checkpoint.
        """
        if not checkpoint_value:
            return ""
        return checkpoint_value.get(ALERT_START_DATE_CHECKPOINT_KEY, "")

    def exit_gracefully(self, signum, frame):
        """
        This method stores the checkpoint if not done already before terminating the input
        """
        self._logger.info("Execution about to get stopped due to SIGTERM.")
        try:
            if self.events_ingested and not self.checkpoint_updated:
                self._logger.info("Updating the checkpoint before exiting gracefully.")
                checkpoint_handler(
                    self._logger,
                    self.session_key,
                    self.checkpoint_dict,
                    self.checkpoint_key,
                )
                self._logger.info(
                    "Successfully updated the checkpoint before exiting. Updated checkpoint = {}".format(
                        self.checkpoint_dict
                    )
                )
        except Exception as exc:
            log.log_exception(
                self._logger,
                exc,
                exc_label=constants.UCC_EXECPTION_EXE_LABEL.format(
                    self.input_params.get("name").replace("://", ":")
                ),
                msg_before="Unable to save checkpoint before SIGTERM termination.",
            )
        sys.exit(0)

    def handle_audit_resp(self, response):
        """
        Ingests the audit data into the splunk
        Updating the Checkpoint dictionary accordingly
        """
        try:
            last_count = self.checkpoint_dict["last_count"]
            self.events_ingested = 0
            events_list = []

            ew = event_writer.ClassicEventWriter()
            entries = response.json()[last_count:]

            for entry in entries:
                event = ew.create_event(
                    data=json.dumps(entry),
                    sourcetype=constants.GITHUB_AUDIT_LOG_SOURCE_TYPE,
                    source=self.input_params["name"].replace("://", ":")
                    + ":"
                    + self.input_params["account"],
                    index=self.input_params["index"],
                )
                events_list.append(event)

            ew.write_events(events_list)
            self.events_ingested = len(entries)
            self._logger.info("Ingested {} audit events.".format(self.events_ingested))
            self.checkpoint_dict["last_count"] = len(response.json())
        except Exception as e:
            log.log_exception(
                self._logger,
                e,
                exc_label=constants.UCC_EXECPTION_EXE_LABEL.format(
                    self.input_params.get("name").replace("://", ":")
                ),
                msg_before="Error while ingesting the audit data into the Splunk.",
            )
            sys.exit(1)

    def collect_audit_data(self, account_type, org_name):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
        # for windows machine
        if os.name == "nt":
            signal.signal(signal.SIGBREAK, self.exit_gracefully)  # pylint:disable=E1101

        event_counter = 0
        last = 0

        self.checkpoint_key = self.input_params["name"]
        checkpoint_collection = checkpointer.KVStoreCheckpointer(
            CHECKPOINTER, self.session_key, APP_NAME
        )
        checkpoint_value = checkpoint_collection.get(self.checkpoint_key)
        if checkpoint_value:
            self.checkpoint_dict = {
                "last_count": checkpoint_value["last_count"],
                "last_after": checkpoint_value["last_after"],
            }
        else:
            self.checkpoint_dict = {
                "last_count": 0,
                "last_after": "",
            }

        api_url = constants.GITHUB_AUDIT_LOG_ENDPOINT.format(account_type, org_name)
        params = {
            "phrase": (
                f"created:>={self.input_params.get('start_date')}"
                if self.input_params.get("start_date")
                else ""
            ),
            "include": self.input_params["events_type"],
            "after": self.checkpoint_dict["last_after"],
            "order": "asc",
            "per_page": str(PER_PAGE),
        }

        while last == 0:
            self.checkpoint_updated = False
            params["after"] = self.checkpoint_dict["last_after"]
            self._logger.info(
                f"Collecting Audit events with URL = {api_url} and params = {params}"
            )
            response = self.make_api_call(
                url=api_url,
                headers=self.headers,
                proxies=self.proxies,
                params=params,
            )
            self.handle_audit_resp(response)
            event_counter += self.events_ingested

            if "next" in response.links:
                next_hash = parse_qs(urlparse(response.links["next"]["url"]).query)[
                    "after"
                ][0]
                self._logger.debug("next_hash value is found - {}".format(next_hash))
                self.checkpoint_dict = {
                    "last_count": 0,
                    "last_after": next_hash,
                }
            else:
                if self.events_ingested:
                    self._logger.info(
                        "Successfully ingested {} audit events.".format(event_counter)
                    )
                    ### Add ingestion log
                    log.events_ingested(
                        self._logger,
                        self.input_params["name"],
                        constants.GITHUB_AUDIT_LOG_SOURCE_TYPE,
                        event_counter,
                        self.input_params["index"],
                        account=self.account_name,
                        license_usage_source=self.license_usage_source,
                    )

                else:
                    self._logger.info("No new events found.")
                last = 1

            if "next" in response.links or self.events_ingested:
                checkpoint_handler(
                    self._logger,
                    self.session_key,
                    self.checkpoint_dict,
                    self.checkpoint_key,
                )
                self._logger.info(
                    "Successfully updated the checkpoint. Updated checkpoint = {}".format(
                        self.checkpoint_dict
                    )
                )
            self.checkpoint_updated = True

    def collect_user_data(self, org_name, event_writer):
        error_flag_for_user_data = 0
        api_url = "https://api.github.com"
        slug = "/orgs/{org}/members".replace("{org}", org_name)
        page = 1
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(self.security_token),
        }
        status_forcelist = [429, 502, 503, 504]
        event_counter = 0
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=status_forcelist)
        session.mount("https://", HTTPAdapter(max_retries=retries))
        while True:
            params = {"per_page": str(PER_PAGE), "page": page}
            try:
                self._logger.info(
                    f"Collecting User events with URL = {api_url+slug} and params={params}"
                )
                response = session.get(
                    "{}{}".format(api_url, slug),
                    headers=headers,
                    proxies=self.proxies,
                    params=params,
                )
                if response.ok and len(response.json()) > 0:
                    new_slug = "/orgs/{org}/memberships/".replace("{org}", org_name)
                    for entry in response.json():
                        new_response = session.get(
                            "{}{}{}".format(api_url, new_slug, entry["login"]),
                            headers=headers,
                            proxies=self.proxies,
                        )
                        if new_response.ok:
                            event_written = write_event(
                                self._logger,
                                event_writer,
                                new_response.json(),
                                "github:cloud:user",
                                self.input_params,
                            )
                        if new_response.status_code == 400:
                            self._logger.error(
                                "ERROR [{}] - GitHub server cannot or will not \
                                    process the request due to Bad Request. {}".format(
                                    new_response.status_code, new_response.json()
                                )
                            )
                            break
                        if new_response.status_code == 403:
                            self._logger.error(
                                "ERROR [{}] - {}".format(
                                    new_response.status_code, new_response.json()
                                )
                            )
                            break
                        if new_response.status_code == 404:
                            self._logger.error(
                                "ERROR [{}] - Requested resource not found {}".format(
                                    new_response.status_code, new_response.json()
                                )
                            )
                            break
                        if not event_written:
                            error_flag_for_user_data = 1
                            break
                        event_counter += 1
                    if (
                        "last" not in response.links
                        or not response.links
                        or error_flag_for_user_data == 1
                    ):
                        self._logger.info(
                            "Successfully ingested {} user events".format(event_counter)
                        )
                        log.events_ingested(
                            self._logger,
                            self.input_params["name"],
                            constants.GITHUB_USER_SOURCE_TYPE,
                            event_counter,
                            self.input_params["index"],
                            account=self.account_name,
                            license_usage_source=self.license_usage_source,
                        )
                        break
                    else:
                        last_page = parse_qs(
                            urlparse(response.links["last"]["url"]).query
                        )["page"][0]
                        page += 1
                        if page == last_page or page == 1:
                            self._logger.info(
                                "Successfully ingested {} user events".format(
                                    event_counter
                                )
                            )
                            log.events_ingested(
                                self._logger,
                                self.input_params["name"],
                                constants.GITHUB_USER_SOURCE_TYPE,
                                event_counter,
                                self.input_params["index"],
                                account=self.account_name,
                                license_usage_source=self.license_usage_source,
                            )
                            break
                elif response.ok:
                    self._logger.error(
                        "Could not fetch user log data. Make sure required scopes are provided to access token."
                    )
                    break
                else:
                    self._logger.error(
                        "ERROR [{}] - {}".format(response.status_code, response.json())
                    )
                    break

            except Exception as e:
                log.log_exception(
                    self._logger,
                    e,
                    exc_label=constants.UCC_EXECPTION_EXE_LABEL.format(
                        self.input_params.get("name").replace("://", ":")
                    ),
                    msg_before="Failed to fetch user data.",
                )
                raise RuntimeError(
                    "Could not fetch user log data. Please \
                        check your configuration, access token scope / correctness \
                        and API rate limits. status_code: {} - url: {} - Response: {}".format(
                        response.status_code, response.url, response.text
                    )
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
                raise_on_status=False,
            )
            if retry_strategy:
                adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)
                self.session = requests.Session()
                self.session.mount("https://", adapter)
                self.session.mount("http://", adapter)

        except Exception as e:
            log.log_exception(
                self._logger,
                e,
                exc_label=constants.UCC_EXECPTION_EXE_LABEL.format(
                    self.input_params.get("name").replace("://", ":")
                ),
                msg_before="Failed to create requests session.",
            )
            sys.exit("Failed to create requests session. Terminating.")

    def make_api_call(self, url, headers, params, proxies):
        """
        This function makes an API call to GitHub Server
        Args:
            url (string): URL to get the data from GitHub server
            headers (dictionary): headers for the API call
            params (dictionary): parameters for the API call
            proxies (dictionary): proxy details for the API call

        Returns:
            response object: response object obtained from the API call
        """
        try:
            response = self.session.get(
                url=url,
                headers=headers,
                proxies=proxies,
                params=params,
            )
            if response.status_code not in (200, 201):
                raise RuntimeError(
                    "Unable to fetch data. Please check your configuration, \
                        access token scope / correctness and API rate limits. \
                            status_code: {} - url: {} - Response: {}".format(
                        response.status_code, response.url, response.text
                    )
                )
            return response
        except Exception as e:
            log.log_exception(
                self._logger,
                e,
                exc_label=constants.UCC_EXECPTION_EXE_LABEL.format(
                    self.input_params.get("name").replace("://", ":")
                ),
                msg_before="Failed to create requests session.",
            )
            sys.exit(
                "Could not connect to GitHub. Check configuration and network settings"
            )

    def handle_response(self, response):
        """
        Ingests the code-scanning alerts data into the splunk
        Updates the Checkpoint accordingly
        """

        try:
            latest_updated_at = self.checkpoint_dict["last_updated_at"]
            self.events_ingested = 0
            events_list = []
            ew = event_writer.ClassicEventWriter()
            for entry in response.json():
                if entry["updated_at"] > self.checkpoint_dict["last_updated_at"]:
                    # Write event only when last updated date of ingested events is less than the event ingested date.
                    event = ew.create_event(
                        data=json.dumps(entry),
                        sourcetype=sourcetype_dict.get(
                            self.input_params.get("alert_type", "code_scanning_alerts"),
                            constants.GITHUB_CS_ALERT_SOURCE_TYPE,
                        ),
                        source=self.input_params["name"].replace("://", ":")
                        + ":"
                        + self.input_params["account"],
                        index=self.input_params["index"],
                    )
                    events_list.append(event)
                    latest_updated_at = entry["updated_at"]

            ew.write_events(events_list)
            self.events_ingested = len(events_list)
            self._logger.info(
                "Ingested {} {} alerts events.".format(
                    self.events_ingested,
                    self.input_params.get("alert_type", "code_scanning_alerts"),
                )
            )
            self.checkpoint_dict["last_updated_at"] = latest_updated_at

        except Exception as e:
            log.log_exception(
                self._logger,
                e,
                exc_label=constants.UCC_EXECPTION_EXE_LABEL.format(
                    self.input_params.get("name").replace("://", ":")
                ),
                msg_before="Error while ingesting the code-scanning alerts data into the Splunk.",
            )
            sys.exit(1)

    def collect_alerts_data(self, account_type, org_name):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
        # for windows machine
        if os.name == "nt":
            signal.signal(signal.SIGBREAK, self.exit_gracefully)  # pylint:disable=E1101

        event_counter = 0
        last = 0

        # Get start_date from input parameters
        input_start_date = self._format_alert_start_date(
            self.input_params.get("start_date")
        )

        api_url = constants.GITHUB_ALERTS_ENDPOINT.format(
            account_type,
            org_name,
            constants.API_ALERT_TYPE[
                self.input_params.get("alert_type", "code_scanning_alerts")
            ],
        )

        self._logger.info("Alerts API url {}".format(api_url))

        self.checkpoint_key = self.input_params["name"]
        checkpoint_collection = checkpointer.KVStoreCheckpointer(
            CHECKPOINTER, self.session_key, APP_NAME
        )
        checkpoint_value = checkpoint_collection.get(self.checkpoint_key)
        applied_start_date = self._get_applied_alert_start_date(checkpoint_value)
        checkpoint_reset = False

        if input_start_date and applied_start_date != input_start_date:
            self.checkpoint_dict = {
                "last_after": "",
                "last_updated_at": input_start_date,
                ALERT_START_DATE_CHECKPOINT_KEY: input_start_date,
            }
            checkpoint_reset = True
        elif checkpoint_value:
            self.checkpoint_dict = {
                "last_after": checkpoint_value.get("last_after", ""),
                "last_updated_at": checkpoint_value.get(
                    "last_updated_at", DEFAULT_ALERT_LAST_UPDATED_AT
                ),
            }
            if applied_start_date:
                self.checkpoint_dict[
                    ALERT_START_DATE_CHECKPOINT_KEY
                ] = applied_start_date
        else:
            self.checkpoint_dict = {
                "last_after": "",
                "last_updated_at": DEFAULT_ALERT_LAST_UPDATED_AT,
            }

        alert_utils = AlertUtils(
            self.input_params,
            PER_PAGE,
            self.checkpoint_dict,
        )
        params = alert_utils.get_params()
        self._logger.info(
            "Final set of request parameters {} for {} url".format(params, api_url)
        )
        while last == 0:
            self.checkpoint_updated = False
            params["after"] = self.checkpoint_dict["last_after"]
            self._logger.info(
                f"Collecting Alerts events with URL = {api_url} and params = {params}"
            )
            response = self.make_api_call(
                url=api_url,
                headers=self.headers,
                proxies=self.proxies,
                params=params,
            )
            self.handle_response(response)
            event_counter += self.events_ingested

            if "next" in response.links:
                next_hash = parse_qs(urlparse(response.links["next"]["url"]).query)[
                    "after"
                ][0]
                self._logger.debug("next_hash value is found - {}".format(next_hash))
                checkpoint_start_date = self.checkpoint_dict.get(
                    ALERT_START_DATE_CHECKPOINT_KEY
                )
                self.checkpoint_dict = {
                    "last_after": next_hash,
                    "last_updated_at": self.checkpoint_dict["last_updated_at"],
                }
                if checkpoint_start_date:
                    self.checkpoint_dict[
                        ALERT_START_DATE_CHECKPOINT_KEY
                    ] = checkpoint_start_date
            else:
                if self.events_ingested:
                    self._logger.info(
                        "Successfully ingested {} {} events.".format(
                            event_counter,
                            self.input_params.get("alert_type", "code_scanning_alerts"),
                        )
                    )
                    log.events_ingested(
                        self._logger,
                        self.input_params["name"],
                        sourcetype_dict.get(
                            self.input_params.get("alert_type", "code_scanning_alerts"),
                            constants.GITHUB_CS_ALERT_SOURCE_TYPE,
                        ),
                        event_counter,
                        self.input_params["index"],
                        account=self.account_name,
                        license_usage_source=self.license_usage_source,
                    )
                else:
                    self._logger.info("No new events found.")
                last = 1

            if "next" in response.links or self.events_ingested or checkpoint_reset:
                checkpoint_handler(
                    self._logger,
                    self.session_key,
                    self.checkpoint_dict,
                    self.checkpoint_key,
                )
                self._logger.info(
                    "Successfully updated the checkpoint. Updated checkpoint = {}".format(
                        self.checkpoint_dict
                    )
                )
                checkpoint_reset = False
            self.checkpoint_updated = True
