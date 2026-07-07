#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test  # isort: skip # noqa: F401
import datetime
import json
import os.path
import sys
import time
import traceback
import base64
from operator import itemgetter
from urllib import parse
from constant import *
from functools import wraps

import requests
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

APP_NAME = __file__.split(os.path.sep)[-3]


def add_ucc_error_logger(
    logger,
    logger_type,
    exception=None,
    exc_label=OKTA_IDENTITY_CLOUD_ERROR,
    full_msg=True,
    msg_before=None,
    msg_after=None,
):
    if logger_type != GENERAL_EXCEPTION:
        getattr(log, logger_type)(logger, exception, msg_before=msg_before)
    else:
        getattr(log, logger_type)(
            logger, exception, exc_label=exc_label, msg_before=msg_before
        )


def time_taken(message: str, logger: callable, debug: bool = False) -> callable:
    """
    Calculate time consumed by the given func
    Taking logger as param to provide flexibility

    Args:
        message (str): Message to log
        logger (callable): logger object
        debug (bool, optional): whether to debug the log. Defaults to True.

    Returns:
        callable: object
    """

    def time_it(func: callable) -> callable:
        @wraps(func)
        def _wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            total_time = round(end_time - start_time, 4)
            logger.info(f"{message}, time_taken = {total_time}")
            return result

        return _wrapper

    return time_it


def time_to_string(format: str, timestamp: datetime) -> str:
    """
    Convert the datetime obj to string

    Args:
        format (str): format to be converted
        timestamp (datetime): timestamp

    Returns:
        str: converted timestamp
    """
    formatted_timestamp = timestamp.strftime(format)
    return formatted_timestamp[:-7] + formatted_timestamp[-7:-4] + "Z"


def string_to_time(format: str, timestamp: str) -> datetime:
    """
    Convert the string obj to datetime

    Args:
        timestamp (str): time to be converted

    Returns:
        datetime: converted timestamp
    """
    return datetime.datetime.strptime(timestamp, format)


def set_logger(session_key: str, filename: str):
    """
    This function sets up a logger with configured log level.
    :param filename: Name of the log file
    :return logger: logger object
    """
    logger = log.Logs().get_logger(filename)
    log_level = conf_manager.get_log_level(
        logger=logger,
        session_key=session_key,
        app_name=APP_NAME,
        conf_name=SETTINGS_CONFIG_FILE,
        default_log_level="DEBUG",
    )
    logger.setLevel(log_level)
    logger.info("log level set is : {}".format(log_level))
    return logger


def log_events_ingested(
    logger, input_name: str, sourcetype: str, event_count: int, index: str, account
):
    """
    This function logs the count of events ingested with particular sourcetype.
    :param logger: logger object
    :param input_name: name of the modular input
    :param event_count: count of events ingeted
    :param sourcetype: sourcetype of the events ingested
    :param index: index in which the events are ingested
    :param account: the account used to collect the events
    """
    log.events_ingested(logger, input_name, sourcetype, event_count, index, account)


def get_account_config(session_key: str, logger) -> conf_manager.ConfFile:
    """
    Returns API access token for a specific account_name.
    :param session_key: session key for particular modular input.
    :param account_name: account name configured in the addon.
    """
    try:
        cfm = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-{ACCOUNT_CONFIG_FILE}",
        )
        account_config_file = cfm.get_conf(ACCOUNT_CONFIG_FILE)

        return account_config_file
    except Exception:
        logger.error(
            f"Error occurred while reading {ACCOUNT_CONFIG_FILE}.conf - {traceback.print_exc()}"
        )
        return None


def get_settings(session_key: str, logger) -> conf_manager.ConfFile:
    try:
        cfm = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-{SETTINGS_CONFIG_FILE}",
        )
        settings_config_file = cfm.get_conf(SETTINGS_CONFIG_FILE)

        return settings_config_file
    except Exception as e:
        msg = f"Error occurred while reading {SETTINGS_CONFIG_FILE}.conf - {traceback.print_exc()}"
        add_ucc_error_logger(
            logger,
            CONFIGURATION_ERROR,
            e,
            exc_label=UCC_EXECPTION_EXE_LABEL.format("settings"),
            msg_before=msg,
        )
        return None


def get_proxy_settings(session_key: str, logger):
    """
    This function reads proxy settings if any, otherwise returns None
    :param session_key: Session key for the particular modular input
    :return: The proxy uri (string)
    """
    try:
        settings_cfm = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-splunk_ta_okta_identity_cloud_settings",
        )
        splunk_ta_okta_identity_cloud_settings_conf = settings_cfm.get_conf(
            SETTINGS_CONFIG_FILE
        ).get_all()

        proxy_settings = {}
        proxy_stanza = {}
        for k, v in splunk_ta_okta_identity_cloud_settings_conf["proxy"].items():
            proxy_stanza[k] = v

        if int(proxy_stanza.get("proxy_enabled", 0)) == 0:
            logger.info("Proxy is disabled. Returning None")
            return proxy_settings
        proxy_type = "http"
        proxy_port = proxy_stanza.get("proxy_port")
        proxy_url = proxy_stanza.get("proxy_url")
        proxy_username = proxy_stanza.get("proxy_username", "")
        proxy_password = proxy_stanza.get("proxy_password", "")

        if proxy_username and proxy_password:
            proxy_username = parse.quote_plus(proxy_username)  # noqa
            proxy_password = parse.quote_plus(proxy_password)  # noqa
            proxy_uri = "{}://{}:{}@{}:{}".format(
                proxy_type,
                proxy_username,
                proxy_password,
                proxy_url,
                proxy_port,
            )
        else:
            proxy_uri = "{}://{}:{}".format(proxy_type, proxy_url, proxy_port)

        proxy_settings = {"http": proxy_uri, "https": proxy_uri}
        logger.info("Successfully fetched configured proxy details.")
        return proxy_settings
    except Exception as e:
        msg = f"Failed to fetch proxy details from configuration. {traceback.format_exc()}"
        add_ucc_error_logger(
            logger,
            CONFIGURATION_ERROR,
            e,
            exc_label=UCC_EXECPTION_EXE_LABEL.format("settings"),
            msg_before=msg,
        )
        sys.exit(1)


def remove_redirect_uris(raw_event, logger):
    """
    This function removes the selected URI fields from the raw event.

    Args:
        raw_event(dict): Individual app event
        logger(object): Logger object
    """
    try:
        if "oauthClient" in raw_event.get("settings"):
            del raw_event["settings"]["oauthClient"]["redirect_uris"]
            del raw_event["settings"]["oauthClient"]["post_logout_redirect_uris"]
            del raw_event["settings"]["oauthClient"]["logo_uri"]
            del raw_event["settings"]["oauthClient"]["client_uri"]
    except Exception as e:
        msg = f"Exception occurred while removing redirect URIs from App events. Error Message : {e}"
        add_ucc_error_logger(
            logger,
            CONFIGURATION_ERROR,
            e,
            exc_label=UCC_EXECPTION_EXE_LABEL.format("settings"),
            msg_before=msg,
        )


class EventCollector:
    AUTH_HANDLERS = {
        AUTH_TYPE_BASIC: "_load_basic_auth",
        AUTH_TYPE_OAUTH_CLIENT: "_load_oauth_client_credentials",
        AUTH_TYPE_OAUTH_AUTHZ: "_load_oauth_authorization_code",
    }
    MAX_API_RETRIES = 3
    RETRYABLE_STATUS_CODES = {408, 500, 502, 503, 504}
    RETRYABLE_REQUEST_EXCEPTIONS = (
        requests.exceptions.ConnectionError,
        requests.exceptions.ConnectTimeout,
        requests.exceptions.ReadTimeout,
        requests.exceptions.Timeout,
        requests.exceptions.ChunkedEncodingError,
        requests.exceptions.ContentDecodingError,
    )

    def __init__(self, ew, session_key, input, logger):
        self.session_key = session_key
        self.input = input
        self.logger = logger
        self.ew = ew
        self.account_name = self.input["global_account"]
        self.account_domain = None
        self.api_token = None
        try:
            self.account_config = get_account_config(self.session_key, self.logger).get(
                self.account_name
            )
            self.additional_parameters = get_settings(
                self.session_key, self.logger
            ).get("additional_parameters")
            self.auth_type = self.account_config.get("auth_type")
            self.proxies = get_proxy_settings(self.session_key, self.logger)
            # Auth types = oauth_client_credentials, oauth, basic
            self._load_auth_parameters()
        except Exception:
            self.logger.error(traceback.format_exc())
            sys.exit(1)

    def _load_auth_parameters(self):
        handler_method_name = self.AUTH_HANDLERS.get(self.auth_type)
        if not handler_method_name:
            self.logger.warning("Unknown auth_type provided: %s", self.auth_type)
            return
        try:
            getattr(self, handler_method_name)()
        except Exception as e:
            msg = f"Error occurred while loading auth parameters: {e}"
            add_ucc_error_logger(
                self.logger,
                AUTHENTICATION_ERROR,
                e,
                exc_label=UCC_EXECPTION_EXE_LABEL.format("auth"),
                msg_before=msg,
            )
            sys.exit(1)

    def _load_basic_auth(self):
        self.account_domain = self.account_config.get("domain")
        self.api_token = self.account_config.get("password")
        if not (self.account_domain and self.api_token):
            raise Exception(
                f"Domain or API token is missing in account configuration. Please validate your configuration for account: {self.account_name}"
            )

    def _load_oauth_client_credentials(self):
        self.account_domain = self.account_config.get("endpoint_url")
        self.client_id = self.account_config.get("client_id_oauth_credentials")
        self.client_secret = self.account_config.get("client_secret_oauth_credentials")
        self.access_token = self.account_config.get("access_token")
        self.scope = self.account_config.get("scope", None)
        if self.scope is None or self.scope == "":
            self.scope = DEFAULT_SCOPE
        if not (
            self.account_domain
            and self.client_id
            and self.client_secret
            and self.access_token
            and self.scope
        ):
            raise Exception(
                f"Could not read account configuration. Please validate your configuration for account: {self.account_name}"
            )

    def _load_oauth_authorization_code(self):
        self.account_domain = self.account_config.get("endpoint")
        self.scope = self.account_config.get("scope")
        self.client_id = self.account_config.get("client_id")
        self.client_secret = self.account_config.get("client_secret")
        self.access_token = self.account_config.get("access_token")
        self.refresh_token = self.account_config.get("refresh_token")
        if not (
            self.account_domain
            and self.client_id
            and self.client_secret
            and self.access_token
            and self.refresh_token
            and self.scope
        ):
            raise Exception(
                f"Could not read account configuration. Please validate your configuration for account: {self.account_name}"
            )

    def _get_next_page_url(self, response):
        try:
            return response.links["next"]["url"]  # url for the next page
        except (KeyError, AssertionError):
            self.logger.info("No more pages to collect the data")
            return None

    def _get_headers(self):
        content_type = "application/json"
        userAgent = "Splunk Add-on for Okta Identity Cloud"
        authorization_value = (
            f"Bearer {self.access_token}"
            if self.auth_type in OAUTH_TYPES
            else f"SSWS {self.api_token}"
        )
        return {
            "Accept": "application/json",
            "Content-Type": content_type,
            "User-Agent": userAgent,
            "Authorization": authorization_value,
        }

    def _get_retry_delay(self, retry, response=None):
        retry_after = None
        if response is not None:
            retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(int(retry_after), 0)
            except (TypeError, ValueError):
                self.logger.debug(
                    f"Ignoring invalid Retry-After header value: {retry_after}"
                )
        return min(2**retry, 30)

    def _retry_api_call(self, url, retry, reason, response=None):
        delay = self._get_retry_delay(retry, response=response)
        self.logger.warning(
            f"Retrying API call to {url}. Attempt {retry + 2}/{self.MAX_API_RETRIES}. "
            f"Reason: {reason}. Sleeping for {delay} seconds before retry."
        )
        if delay > 0:
            time.sleep(delay)

    def get_metric_url(self, metric):
        return METRIC_URL.format(account_domain=self.account_domain, metric=metric)

    def get_token_url(self):
        return TOKEN_URL.format(account_domain=self.account_domain)

    def fetch_log_events(self, start_date, end_date, next_link=None):
        """
        create params based on above details
        create headers
        """
        metric = self.input["metric"]
        response_limit = self.additional_parameters.get(f"{metric[:-1]}_limit")
        url = self.get_metric_url(metric)
        params = {"since": start_date, "until": end_date, "limit": response_limit}
        if next_link:
            params = None
            url = next_link
        headers = self._get_headers()
        items = []
        try:
            response = self.make_api_call(url, headers, params)
            items = response.json()
            next_link = self._get_next_page_url(response)
        except Exception as e:
            msg = f"Exception occured while fetching logs - {str(e)}"
            add_ucc_error_logger(
                self.logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=UCC_EXECPTION_EXE_LABEL.format("general"),
                msg_before=msg,
            )
            raise e
        self.logger.debug(f"Requesting from API: {url}, params={params}")
        return items, next_link

    def fetch_events(self, ts=None, next_url=None, **kwargs):
        """
        This function will fetch events based on the metric selected

        Args:
            ts (string, optional): Checkpoint string if present. Defaults to None.
            next_url (string, optional): Next URL to utilise in API call if any. Defaults to None.

        Returns:
            Response object, is_alive, next_url: Returns the response object ot the API call,
                                                if the response has next url of not (True or False),
                                                next_url to make the next API call
        """
        metric = self.input["metric"]
        url = self.get_metric_url(metric)
        params = dict()
        response_limit = self.additional_parameters.get(f"{metric[:-1]}_limit")
        params["limit"] = response_limit

        if metric == "users":
            content_type = 'application/json; okta-response="omitCredentials,omitCredentialsLinks, omitTransitioningToStatus"'  # noqa
            params["sortBy"] = "lastUpdated"
            if ts:
                params["search"] = f'lastUpdated gt "{ts}"'
            else:
                ts = DEFAULT_FALLBACK_DATE
                params["search"] = f'lastUpdated gt "{ts}"'
        elif metric == "groups":
            content_type = 'application/json; okta-response="omitCredentials,omitCredentialsLinks, omitTransitioningToStatus"'  # noqa
            params["sortBy"] = "lastUpdated"
            if int(self.input.get("fetch_stats", 1)):
                params["expand"] = "stats"
            if ts and (isinstance(ts, str)):
                # if checkpoint is a string, we modify it to a dictionary
                # this scenario occurs when upgrading the TA
                self.logger.info("Checkpoint found, moving to dictionary")
                params[
                    "search"
                ] = f'lastUpdated gt "{ts}" or lastMembershipUpdated gt "{ts}"'
            elif ts and ts["lastUpdated"] and not ts.get("lastMembershipUpdated"):
                # if checkpoint has lastUpdated param only
                params[
                    "search"
                ] = f'lastUpdated gt "{ts["lastUpdated"]}"  or lastMembershipUpdated gt "{ts["lastUpdated"]}"'
            elif ts and ts["lastUpdated"] and ts["lastMembershipUpdated"]:
                # if checkpoint has lastUpdated and lastMembershipUpdated both
                params[
                    "search"
                ] = f'lastUpdated gt "{ts["lastUpdated"]}" or lastMembershipUpdated gt "{ts["lastMembershipUpdated"]}"'
            else:
                # if checkpoint is None, for newly created inputs
                ts = {}
                ts["lastUpdated"] = DEFAULT_FALLBACK_DATE
                ts["lastMembershipUpdated"] = DEFAULT_FALLBACK_DATE
                self.logger.debug("Checkpoint dictionary : {}".format(ts))
                params[
                    "search"
                ] = f'lastUpdated gt "{ts["lastUpdated"]}" or lastMembershipUpdated gt "{ts["lastMembershipUpdated"]}"'

        headers = self._get_headers()

        if next_url:
            url = next_url
            params = None

        self.logger.debug(f"Requesting from API: {url}, params={params}")

        response = self.make_api_call(url, headers, params)
        if not response or response.status_code not in (200, 201):
            return response, False, None

        # Check for more pages. If none, we can exit the flow. If yes, get url of the next page
        try:
            assert len(response.json()) == int(response_limit)
            url = response.links["next"]["url"]  # url for the next page
        except (KeyError, AssertionError):
            self.logger.info("No more pages to collect the data")
            return response, False, None

        return response, True, url

    def make_api_call(self, url, headers, params):
        """
        This function makes an API call to Okta Server
        Args:
            url (string): URL to get the data from Okta server
            headers (dictionary): headers for the API call
            params (dictionary): parameters for the API call

        Returns:
            response object: response object obtained from the API call
        """
        content = {}
        for retry in range(self.MAX_API_RETRIES):
            try:
                response = requests.request(
                    "GET",
                    url,
                    headers=headers,
                    params=params,
                    proxies=self.proxies,
                    timeout=REQTIMEOUT,
                )
                content = response
                if response.status_code in (200, 201):
                    self.request_throttling(response, after_every_call=True)
                    return content

                if response.status_code in (401, 403):
                    if self.auth_type in OAUTH_TYPES:
                        if response.status_code == 401:
                            self.logger.warning(
                                f"Failure caused due to expired access token. "
                                f"Status code - {response.status_code}, Failure reason - {response.reason}. "
                                f"Regenerating Access Token"
                            )
                        else:
                            self.logger.error(
                                f"Failure caused due to incorrect Okta Web App Scopes. "
                                f"Status code - {response.status_code}, Failure reason - {response.reason}. "
                                f"Provide necessary scopes and reconfigure the account - '{self.account_name}' to continue the data collection"
                            )
                            return content
                        access_token_updated_status = self.refresh_access_token()
                        if not access_token_updated_status:
                            return content
                        latest_access_token = (
                            get_account_config(self.session_key, self.logger)
                            .get(self.account_name)
                            .get("access_token")
                        )
                        self.access_token = latest_access_token
                        headers.update(
                            {"Authorization": f"Bearer {latest_access_token}"}
                        )
                        continue
                    elif self.auth_type == AUTH_TYPE_BASIC:
                        raise Exception(
                            f"Could not authenticate using api token, reason: {content.json().get('errorSummary')}"
                        )

                if response.status_code == 429:
                    self.request_throttling(response)
                    if retry < self.MAX_API_RETRIES - 1:
                        continue
                    return content

                if response.status_code in self.RETRYABLE_STATUS_CODES:
                    if retry < self.MAX_API_RETRIES - 1:
                        self._retry_api_call(
                            url,
                            retry,
                            f"Status code - {response.status_code}, Failure reason - {response.reason}",
                            response=response,
                        )
                        continue
                    self.logger.error(
                        f"Failure occurred while connecting to {url}. "
                        f"The reason for failure={response.reason}"
                    )
                    return content

                self.logger.error(
                    f"Failure occurred while connecting to {url}. The reason for failure={response.reason}"
                )
                return content
            except self.RETRYABLE_REQUEST_EXCEPTIONS as e:
                if retry < self.MAX_API_RETRIES - 1:
                    self._retry_api_call(url, retry, str(e))
                    continue
                msg = f"Failure occurred while connecting to {url}.\nTraceback: {traceback.format_exc()}"
                add_ucc_error_logger(
                    self.logger,
                    CONNECTION_ERROR,
                    e,
                    exc_label=UCC_EXECPTION_EXE_LABEL.format("connection"),
                    msg_before=msg,
                )
                raise
            except requests.exceptions.RequestException as e:
                msg = f"Failure occurred while connecting to {url}.\nTraceback: {traceback.format_exc()}"
                add_ucc_error_logger(
                    self.logger,
                    CONNECTION_ERROR,
                    e,
                    exc_label=UCC_EXECPTION_EXE_LABEL.format("connection"),
                    msg_before=msg,
                )
                raise
            except Exception as e:
                msg = f"Failure occurred while connecting to {url}.\nTraceback: {traceback.format_exc()}"
                add_ucc_error_logger(
                    self.logger,
                    GENERAL_EXCEPTION,
                    e,
                    exc_label=UCC_EXECPTION_EXE_LABEL.format("general"),
                    msg_before=msg,
                )
                raise
        return content

    def fetch_enrichment_data(self, response, item):
        """
        This function will collect the extra enrichment data.
        For metric=groups, this function will call the function to fetch its users and apps
        For metric=apps, this function will call the function to fetch its users and groups

        Args:
            response (object): Response fetched from fetch_events function
            item (dict): Individual raw event of group or app
        """
        self.logger.info(
            f"""Fetching extra enrichment data for {self.input["metric"]}"""
        )

        headers = response.request.headers

        # If metric=groups, collectGroupApps & collectGroupUsers will be called
        # If metric=apps, collectAppGroups & collectAppUsers will be called
        if self.input["metric"] == "groups":
            # calling collectGroupApps
            self.collectGroupApps(item, headers)
            # # calling collectGroupUsers
            self.collectGroupUsers(item, headers)
        else:  # if metric = apps
            # calling collectAppGroups
            self.collectAppGroups(item, headers)
            # calling collectAppUsers
            self.collectAppUsers(item, headers)

    def update_timestamp(self, metric, raw_events, checkpoint_data):
        """
        This funcion will update the timestamp

        Args:
            metric (str): Metric of the input
            raw_events (list of dict): Events fetched from fetch_event function
            checkpoint_data (object): Checkpoint object of the metric

        Returns:
            object: Updated timestamp object of the respective metric
        """
        # Update ts value based on raw_events fetched to update checkpoint
        if raw_events:
            if metric == "log":
                ts = raw_events[-1]["published"]
            elif metric == "user":
                ts = raw_events[-1]["lastUpdated"]
            elif metric == "group":
                if checkpoint_data["ts"] is None:
                    self.logger.info("Initialising checkpoint dictionary as None")
                    ts = {}
                    ts["lastUpdated"] = ""
                    ts["lastMembershipUpdated"] = ""
                elif isinstance(checkpoint_data["ts"], str):
                    self.logger.debug(
                        "Existing checkpoint was string, migrating it to dictionary"
                    )
                    ts = {}
                    ts["lastUpdated"] = checkpoint_data["ts"]
                else:
                    ts = checkpoint_data["ts"]
                last_membership_updated_event_timestamps = sorted(
                    raw_events, key=itemgetter("lastMembershipUpdated")
                )

                # if lastUpdated time is greater than lastUpdated stored in the checkpoint,
                # then update the checkpoint value
                if raw_events[-1]["lastUpdated"] > ts["lastUpdated"]:
                    ts["lastUpdated"] = raw_events[-1]["lastUpdated"]
                # if lastMembershipUpdated key does not exist in checkpoint data
                # or lastMembershipUpdated is greater than the value in checkpoint,
                # then update the checkpoint value
                if (not ts.get("lastMembershipUpdated")) or (
                    last_membership_updated_event_timestamps[-1][
                        "lastMembershipUpdated"
                    ]
                    > ts["lastMembershipUpdated"]
                ):
                    ts[
                        "lastMembershipUpdated"
                    ] = last_membership_updated_event_timestamps[-1][
                        "lastMembershipUpdated"
                    ]

            else:
                ts = None

            checkpoint_data["ts"] = ts

        return checkpoint_data

    def request_throttling(self, response, after_every_call=False):
        """Manage request throttling based on API account limits
        Time taken for checking rate-limit ~ 0.0002sec

        There are 2 options for request throttling:
            Dynamic (default and preferred):
                - used when `dynamic_rate_enabled` is set
                - calculate the minumum interval between requests to stay below the threshold
                - add sleep interval between consecutive requests
            Static:
                - allow consecutive requests to be sent without waiting
                - when the configured rate limit is reached, wait until the next reset

        Args:
            response ([requests.Response]): [response object, with headers]
        """
        try:
            # Get relevant settings
            throttle_threshold = float(self.additional_parameters.rate_limit_pct)
            dynamic_rate_enabled = int(
                self.additional_parameters.dynamic_rate_enabled
            )  # String '1' or '0'. Convert to int to use as boolean

            # Get current rate limit info from the latest response headers
            limit_header = response.headers.get("x-rate-limit-limit")
            remaining_header = response.headers.get("x-rate-limit-remaining")
            reset_header = response.headers.get("x-rate-limit-reset")

            # If any required header is missing, skip processing
            if limit_header is None or remaining_header is None or reset_header is None:
                self.logger.debug(
                    "One or more rate limit headers are missing. Skipping rate logic."
                )
                return

            # Safe to convert to int now
            limit = int(limit_header)
            remaining = int(remaining_header)
            reset = int(reset_header)
            used = limit - remaining
            current_request_rate_pct = (used / limit) * 100

            sleep_interval = 0
            # the reset time might be less than "current UTC time" because of delay in the response
            # it leads to negative sleep interval
            # hence we are adding 1 to the value
            seconds_left_before_reset = reset - int(time.time()) + 1
            if current_request_rate_pct >= throttle_threshold:
                self.logger.debug(
                    f"Rate Limit Threshold reached/passed. "
                    f"Configured: {throttle_threshold}% | Current: {current_request_rate_pct}%"
                )
                sleep_interval = seconds_left_before_reset
            else:
                # Dynamic rate limiting introduces a delay between most requests to evenly distribute
                # API calls over time, helping to prevent hitting per-minute rate limits.
                if dynamic_rate_enabled and not after_every_call:
                    self.logger.debug("Using dynamic request throttling")
                    adaptive_limit = limit * throttle_threshold / 100
                    adaptive_remaining = adaptive_limit - (limit - remaining)
                    sleep_interval = seconds_left_before_reset / adaptive_remaining
                    if sleep_interval <= 0:
                        sleep_interval = 1
            if sleep_interval > 0:
                self.logger.debug(
                    f"Sleeping for {sleep_interval} seconds before continuing"
                )
                time.sleep(sleep_interval)
        except Exception as e:
            msg = f"An error occurred while throttling the request: {str(e)}"
            add_ucc_error_logger(
                self.logger,
                SERVER_ERROR,
                e,
                exc_label=UCC_EXECPTION_EXE_LABEL.format("server"),
                msg_before=msg,
            )
            raise e

    def collectGroupUsers(self, response, headers):
        """
        This function will collect users related to a particular group.
        It will ingest the userid, groupid and lastMembershipUpdated in
        sourcetype = OktaIM2:groupUser

        Args:
            response (dict): Individual group event
            headers (object): Headers to use in API calls
        """
        total_groupUser_count = 0
        self.logger.info(
            "Collecting users for group name = {}, id = {}".format(
                response["profile"]["name"], response["id"]
            )
        )
        resource = ""
        # We use maximum limit to get maximum data in lesser number of API calls
        params = {"limit": MAX_USER_LIMIT}
        if "users" in response.get("_links") and "href" in response["_links"]["users"]:
            resource = response["_links"]["users"]["href"]
            self.logger.info(f"Making API Call with URL - {resource}")
            groupUsers = self.make_api_call(resource, headers, params)
            has_next = True
            while has_next:
                if groupUsers.status_code not in (200, 201):
                    self.logger.error(
                        "Error occurred with status code {}. Response from server : {}".format(
                            groupUsers.status_code, groupUsers.json()
                        )
                    )
                    break
                groupUser_count = 0
                for groupUser in groupUsers.json():
                    data = {
                        "groupid": response["id"],
                        "groupName": response["profile"]["name"],
                        "userid": groupUser["id"],
                        "userName": groupUser["profile"]["email"],
                        "lastMembershipUpdated": response["lastMembershipUpdated"],
                    }
                    self.ingest_data(data, response)
                    groupUser_count = groupUser_count + 1
                total_groupUser_count = total_groupUser_count + groupUser_count
                log_events_ingested(
                    self.logger,
                    MODULAR_INPUT_NAME.format(self.input["input_name"]),
                    "OktaIM2:groupUser",
                    groupUser_count,
                    self.input["index"],
                    self.account_name,
                )
                next_url = groupUsers.links.get("next", {}).get("url")
                if next_url:
                    self.logger.debug("URL for next page : {}".format(next_url))
                    resource = next_url
                    self.logger.info(f"Making API Call with URL - {resource}")
                    groupUsers = self.make_api_call(resource, headers, {})
                    continue
                else:
                    self.logger.info("No more pages to collect for groupUsers")
                    break
            self.logger.info(
                "Total groupUsers ingested : {}".format(total_groupUser_count)
            )
            if groupUsers.status_code in (200, 201):
                self.request_throttling(groupUsers)

    def collectAppUsers(self, response, headers):
        """
        This function will collect users related to a particular app
        It will ingest the userid, appid, and other related fields
        in sourcetype = OktaIM2:appUser

        Args:
            response (dict): Individual app event
            headers (object): Headers to use in API calls
        """
        total_appUser_count = 0
        self.logger.info(
            "Collecting users for app name = {}, id = {}".format(
                response["name"], response["id"]
            )
        )

        resource = ""
        # We use maximum limit to get maximum data in lesser number of API calls
        params = {"limit": MAX_USER_LIMIT}
        if "users" in response.get("_links") and "href" in response["_links"]["users"]:
            resource = response["_links"]["users"]["href"]
            self.logger.info(f"Making API Call with URL - {resource}")
            appUsers = self.make_api_call(resource, headers, params)
            has_next = True
            while has_next:
                if appUsers.status_code not in (200, 201):
                    self.logger.error(
                        "Error occurred with status code {}. Response from server : {}".format(
                            appUsers.status_code, appUsers.json()
                        )
                    )
                    break
                appUser_count = 0
                for appUser in appUsers.json():
                    if appUser.get("credentials") and appUser["credentials"].get(
                        "userName"
                    ):
                        username = appUser.get("credentials").get("userName")
                    else:
                        username = "undefined"
                    data = {
                        "appid": response["id"],
                        "appName": response["name"],
                        "appLabel": response["label"],
                        "userid": appUser["id"],
                        "externalId": appUser["externalId"],
                        "userName": username,
                        "created": appUser["created"],
                        "lastUpdated": appUser["lastUpdated"],
                        "statusChanged": appUser["statusChanged"],
                        "scope": appUser["scope"],
                        "status": appUser["status"],
                    }
                    self.ingest_data(data, response)
                    appUser_count = appUser_count + 1
                total_appUser_count = total_appUser_count + appUser_count
                log_events_ingested(
                    self.logger,
                    MODULAR_INPUT_NAME.format(self.input["input_name"]),
                    "OktaIM2:appUser",
                    appUser_count,
                    self.input["index"],
                    self.account_name,
                )
                next_url = appUsers.links.get("next", {}).get("url")
                if next_url:
                    self.logger.debug("URL for next page : {}".format(next_url))
                    resource = next_url
                    self.logger.info(f"Making API Call with URL - {resource}")
                    appUsers = self.make_api_call(resource, headers, {})
                    continue
                else:
                    self.logger.info("No more pages to collect for appUsers")
                    break
            self.logger.info("Total appUsers ingested : {}".format(total_appUser_count))
            if appUsers.status_code in (200, 201):
                self.request_throttling(appUsers)

    def collectGroupApps(self, item, headers):
        """
        This function gets the ids of the apps associated with a particular group
        And appends the list of all such ids in the group event itself

        Args:
            item (dict): Individual group event
            headers (object): Headers to use in API calls
        """
        resource = ""
        # We use maximum limit to get maximum data in lesser number of API calls
        params = {"limit": MAX_APP_LIMIT}
        if "apps" in item.get("_links") and "href" in item["_links"]["apps"]:
            resource = item["_links"]["apps"]["href"]
            self.logger.info(f"Making API Call with URL - {resource}")
            groupApps = self.make_api_call(resource, headers, params)
            has_next = True
            while has_next:
                if groupApps.status_code not in (200, 201):
                    self.logger.error(
                        "Error occurred with status code {}. Response from server : {}".format(
                            groupApps.status_code, groupApps.json()
                        )
                    )
                    break
                assigned_apps = []
                for groupApp in groupApps.json():
                    if groupApp.get("id"):
                        assigned_apps.append(groupApp["id"])
                        item["assigned_apps"] = assigned_apps
                next_url = groupApps.links.get("next", {}).get("url")
                if next_url:
                    self.logger.debug("URL for next page : {}".format(next_url))
                    resource = next_url
                    self.logger.info(f"Making API Call with URL - {resource}")
                    groupApps = self.make_api_call(resource, headers, {})
                    continue
                else:
                    self.logger.info("No more pages to collect for groupApps")
                    break
            if groupApps.status_code in (200, 201):
                self.request_throttling(groupApps)

    def collectAppGroups(self, item, headers):
        """
        This function gets the ids of the groups associated with a particular app
        And appends the list of all such ids in the apps event itself

        Args:
            item (dict): Individual app event
            headers (object): Headers to use in API calls
        """
        resource = ""
        # We use maximum limit to get maximum data in lesser number of API calls
        params = {"limit": MAX_GROUP_LIMIT}
        if "groups" in item.get("_links") and "href" in item["_links"]["groups"]:
            resource = item["_links"]["groups"]["href"]
            self.logger.info(f"Making API Call with URL - {resource}")
            appGroups = self.make_api_call(resource, headers, params)
            has_next = True
            while has_next:
                if appGroups.status_code not in (200, 201):
                    self.logger.error(
                        "Error occurred with status code {}. Response from server : {}".format(
                            appGroups.status_code, appGroups.json()
                        )
                    )
                    break
                assigned_groups = []
                if len(appGroups.json()):
                    for appGroup in appGroups.json():
                        if appGroup.get("id"):
                            assigned_groups.append(appGroup["id"])
                            item["assigned_groups"] = assigned_groups
                else:
                    item["assigned_groups"] = assigned_groups
                next_url = appGroups.links.get("next", {}).get("url")
                if next_url:
                    self.logger.debug("URL for next page : {}".format(next_url))
                    resource = next_url
                    self.logger.info(f"Making API Call with URL - {resource}")
                    appGroups = self.make_api_call(resource, headers, {})
                    continue
                else:
                    self.logger.info("No more pages to collect for appGroups")
                    break
            if appGroups.status_code in (200, 201):
                self.request_throttling(appGroups)

    def ingest_data(self, prepared_data, response):
        """
        This function ingests the prepared_data in to the Splunk for:
        OktaIM2:appUser and OktaIM2:groupUser sourcetypes

        Args:
            prepared_data (dict): Dict to be ingested in the sourcetype
            response (dict): Individual group or app event
        """
        try:
            if self.input["metric"] == "groups":
                sourcetype = "OktaIM2:groupUser"
                time = response["lastMembershipUpdated"]
            else:
                sourcetype = "OktaIM2:appUser"
                time = response["lastUpdated"]
            event = smi.Event(
                data=json.dumps(prepared_data),
                sourcetype=sourcetype,
                index=self.input["index"],
                host=self.account_domain,
                time=time,
            )
            self.ew.write_event(event)
        except Exception as e:
            error_message = "Error while ingesting events in sourcetype - {}. Error message - {}".format(
                sourcetype, e
            )
            raise Exception(error_message)

    def refresh_access_token(self):
        """
        Refreshes the access token by making an api call.
        Stores the new access token and refresh token in conf file
        """
        try:
            url = self.get_token_url()
            payload, headers = self._build_refresh_request()

            response = requests.request(
                "POST",
                url,
                headers=headers,
                data=payload,
                proxies=self.proxies,
                timeout=REQTIMEOUT,
            )
            if response.status_code not in (200, 201):
                self.logger.error(
                    f"Error occurred while regenerating the access token associated "
                    f"with account '{self.account_name}'. To fix this issue, reconfigure the account. "
                    f"Status={response.status_code}, Reason={response.reason}"
                )
                return False
            content = json.loads(response.text)
            updated_fields = self._extract_tokens_from_response(content)

            # updating refresh_token and access_token in account config file
            self._update_account_config(updated_fields)
            self.logger.info(
                f"Updated account - '{self.account_name}' with latest value of access_token"
            )
            return True
        except Exception as e:
            msg = (
                f"Failure occurred while generating new access token. "
                f"The reason for failure={traceback.format_exc()}."
            )
            add_ucc_error_logger(
                self.logger,
                AUTHENTICATION_ERROR,
                e,
                exc_label=UCC_EXECPTION_EXE_LABEL.format("auth"),
                msg_before=msg,
            )
            return False

    def _build_refresh_request(self):
        """
        Returns payload and headers for token refresh based on auth type.
        """
        if self.auth_type == AUTH_TYPE_OAUTH_CLIENT:
            payload = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": self.scope,
            }
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            return payload, headers

        # Authorization Code Flow
        payload = f"grant_type=refresh_token&refresh_token={self.refresh_token}"
        auth_value = self._get_basic_auth_header()

        headers = {
            "Accept": "application/json",
            "Authorization": f"Basic {auth_value}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        return payload, headers

    def _get_basic_auth_header(self):
        """
        Encodes client_id and client_secret to base64 for Basic Auth header.
        """
        raw = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode()

    def _extract_tokens_from_response(self, content):
        """
        Extracts tokens from response content and prepares update fields.
        """
        fields = {
            "access_token": str(content.get("access_token")),
            "client_secret_oauth_credentials": str(
                self.account_config.get("client_secret_oauth_credentials")
            ),
        }

        if self.auth_type == AUTH_TYPE_OAUTH_AUTHZ:
            fields.update(
                {
                    "refresh_token": str(content.get("refresh_token")),
                    "client_secret": str(self.account_config.get("client_secret")),
                }
            )

        return fields

    def _update_account_config(self, fields):
        """
        Updates tokens in Splunk conf file for the account.
        """
        cfm = conf_manager.ConfManager(
            self.session_key,
            APP_NAME,
            realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-{ACCOUNT_CONFIG_FILE}",
        )
        conf = cfm.get_conf(ACCOUNT_CONFIG_FILE)
        conf.update(self.account_name, fields, fields.keys())


class Checkpointer:
    def __init__(self, session_key, logger):
        self.logger = logger
        self.session_key = session_key
        self.checkpoint = None

        try:
            self.checkpoint = checkpointer.KVStoreCheckpointer(
                f"{APP_NAME}_checkpoints", self.session_key, APP_NAME
            )
        except Exception as e:
            msg = f"Error in Checkpointer handling:\n{traceback.format_exc()}"
            add_ucc_error_logger(
                self.logger,
                GENERAL_EXCEPTION,
                e,
                exc_label=UCC_EXECPTION_EXE_LABEL.format("checkpoint"),
                msg_before=msg,
            )
            raise

    def get(self, name, metric, **kwargs):
        if not self.checkpoint.get(name):
            if metric != "app":
                self.logger.info(
                    f"Collection {name} not found. Creating collection with initial details"
                )
            if type(kwargs.get("start_date")) == str:
                start_date = kwargs["start_date"]
                if metric in ["user", "log"]:
                    ts = start_date
                elif metric == "group":
                    ts = {
                        "lastUpdated": start_date,
                        "lastMembershipUpdated": start_date,
                    }
                else:
                    ts = None
            else:
                ts = None

            # TODO - remove ts and keep start_date only
            self[name] = {"ts": ts, "data": [], "start_date": ts}
        if metric != "app":
            self.logger.info(
                f"Found {name} collection with checkpoint : {self.checkpoint.get(name)}."
            )
        return self.checkpoint.get(name)

    def __setitem__(self, name, data):
        self.checkpoint.update(name, data)

    def exists(self, timestamp, data=None):
        pass

    def pop(self, key, value):
        pass

    def push(self, timestamp, data):
        pass

    def get_ckpt_info(self, checkpoint_key: str):
        """
        Get checkpoint details based on provided key

        Args:
            checkpoint_key (str): unique key

        Returns:
            Union[Dict, None]: checkpoint details
        """
        try:
            data = self.checkpoint.query_by_id(id=checkpoint_key)
        except Exception as e:
            if e.status != 404:
                msg = "Unable to get checkpoint details"
                add_ucc_error_logger(
                    self.logger,
                    GENERAL_EXCEPTION,
                    e,
                    exc_label=UCC_EXECPTION_EXE_LABEL.format("checkpoint"),
                    msg_before=msg,
                )
                raise
            return None
        return data

    def save(self, record: dict) -> None:
        """
        Inserts a single record into this collection. If the record does not
        contain an _key field, it will be generated.

        Args:
            record (Dict): A dictionary containing the record to be inserted.

        Returns:
            None
        """
        self.checkpoint.insert(record)

    def batch_save(self, records: list) -> None:
        """
        Inserts a batch of records into this collection. If a record does not contain
        an _key field, it will be generated.

        Args:
            records (List): A list of dictionaries, each containing a record
                to be inserted.

        Returns:
            None
        """
        self.checkpoint.batch_save(*records)

    def delete(self, query: dict = None) -> None:
        """
        Deletes one or more records from the collection using the provided query.
        If no query is provided, all records will be deleted.

        Args:
            query (Dict, optional): A dictionary containing the query to use for
                deleting records. Defaults to None.

        Returns:
            None
        """
        if query:
            query = json.dumps(query)
        self.checkpoint.delete(query)

    def delete_by_id(self, id: str = None):
        """
        Deletes the record with the provided ID.

        Args:
            id (str, optional): The ID of the record to delete. Defaults to None.

        Returns:
            Any: The result of the DELETE request.
        """
        self.checkpoint.delete_by_id(id)

    def update(self, checkpoint_key: str, checkpoint_data: dict) -> dict:
        """
        Replaces the document with the specified checkpoint key with the provided data.

        Args:
            checkpoint_key (str): The checkpoint key of the document to be replaced.
            checkpoint_data (Union[Dict, str]): The new data to replace the existing
            document with.

        Returns:
            Dict: The ID of the replaced document.
        """
        self.checkpoint.update(checkpoint_key, checkpoint_data)
