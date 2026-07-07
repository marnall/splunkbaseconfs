#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test  # isort: skip # noqa: F401
import base64
import json
import os.path as op
import re
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import snow_consts
import snow_oauth_helper as soauth
import snow_utility as su
from solnlib import conf_manager, utils
from splunk import rest as splunk_rest


utils.remove_http_proxy_env_vars()


class SnowBase:
    """
    The SnowBase class is designed to address compatibility issues with newer versions of custom commands that were present in the SnowTicket class.
    It removes the dependency on the splunk.Intersplunk library, resolving the following challenges:

    1. **Removal of splunk.Intersplunk Dependency**:
        - Older alert actions and custom commands (built on protocol version 1) relied on the `splunk.Intersplunk` library
          for populating results or error messages to Splunk.
        - This library is incompatible with newer custom commands (built on protocol version 2), which use a different
          approach to populate results and messages.
        - Using `splunk.Intersplunk` in the new protocol version would result in broken code and direct exceptions.

    2. **Improved Thread Pool Execution**:
        - Used modernized approach to thread pool execution by utilizing `concurrent.futures.ThreadPoolExecutor`.
        - This approach offers improved control, scalability, readability, and
           enhanced error handling compared to the older ThreadPool implementation

    3. **Enhanced Response Handling**:
        - Implements structured and centralized response handling for interactions with ServiceNow APIs.

    Note:
    -----
    Derived classes should implement the following abstract methods to provide case-specific logic:
    - `_write_error`
    - `_get_events`
    - `_get_session_key`
    - `_get_table`
    - `_prepare_data`
    - `_process_results`
    """

    def __init__(self) -> None:
        self.session_key = self._get_session_key()
        self.logger = su.create_log_object(self._get_log_file())
        self.token_lock = threading.RLock()
        if not hasattr(self, "invocation_id"):
            self.invocation_id = ""
        self.snow_account = self._get_service_now_account()

    def _write_error(self, message, exit: bool = False):
        """Log the error and exit if exit is set to True"""
        raise NotImplementedError("Derive class shall implement this method.")

    def _get_events(self):
        """Get the events"""
        raise NotImplementedError("Derive class shall implement this method.")

    def _get_session_key(self):
        """Get the session_key"""
        raise NotImplementedError("Derive class shall implement this method.")

    def _get_table(self, event):
        """Get the table from event"""
        raise NotImplementedError("Derived class shell implement this method.")

    def _get_log_file(self):
        "Return the log filename"
        raise NotImplementedError("Derived class shell implement this method.")

    def _prepare_data(self, event):
        """
        Return dict format event.

        **Note: Follow this structure to create the event_data dictionary:
        {
            "table_name": "",
            "snow_table_config": {
                "method": "",
                "subcommand": "",
                "params": {},
            },
            "payload": {},
        }

        - table_name: The name of the target ServiceNow table.
        - snow_table_config: A dictionary containing API configuration details:
        - method: The HTTP method to perform during the API execution (e.g., GET, POST, PUT).
        - subcommand: Indicates the type of action (e.g., get, update, create).
        - params: A dictionary of additional filters to pass with the GET request.
        - payload: Contains the target table fields to pass in the API request.
        """
        raise NotImplementedError("Derived class shall implement this method.")

    def _process_results(self, results):
        """Process the results"""
        raise NotImplementedError("Derived class shall implement this method.")

    def get_invocation_id(self):
        """Get the invocation_id with format"""
        return "[invocation_id={}] [{}]".format(
            self.invocation_id, threading.current_thread().name
        )

    def _get_ticket_link(self, sys_id, table_name):
        """
        Generate the ServiceNow ticket link

        :param sys_id: sys_id to link the record.
        :return link: Record link to access ServiceNow record.
        """
        link = "{0}{1}.do?sysparm_query=sys_id={2}".format(
            self.snow_account["url"], table_name, sys_id
        )
        return link

    def _get_endpoint(self, table_name, subcommand, sys_id: str = ""):
        """
        Get the ServiceNow table API endpoint

        :param table_name: The name of the table for which to retrieve the endpoint.
        :param subcommand: Optional operation type (e.g., 'create', 'update', 'get').
        :param sys_id: Optional sys_id of the record for update operations.
        :return str:  ServiceNow table API endpoint URL.
        """
        if subcommand == "update":
            return f"api/now/table/{table_name}/{sys_id}"
        else:
            return f"api/now/table/{table_name}"

    def _build_endpoint(self, table_name, subcommand: str = "create", sys_id: str = ""):
        """
        Constructs the full ServiceNow endpoint URL based on the given table_name, subcommand and sys_id.

        :param table_name: The name of the table for which to build the endpoint.
        :param subcommand: Optional operation type (e.g., 'create', 'update', 'get').
        :param sys_id: Optional sys_id of the record for update operations.
        :return str: Full ServiceNow API endpoint URL.
        """
        return "{}{}".format(
            self.snow_account["url"],
            self._get_endpoint(table_name, subcommand, sys_id or "").lstrip("/"),
        )

    def _get_resp_record(
        self, content, return_first: bool = False, error_only: bool = False
    ):
        """
        Parses the response content from ServiceNow API.

        :param content: The HTTP response content, either bytes, str, or dict.
        :param return_first: If True, will return the first item from 'result' list (used for GET lookups).
        :param error_only: return only error message instead of dict if set to true.
        :return dict: A parsed response dictionary, or an error dictionary if parsing or validation fails.
        """
        if isinstance(content, bytes):
            content = content.decode("utf-8")

        if isinstance(content, str):
            try:
                resp = json.loads(content)
            except json.JSONDecodeError as e:
                error_msg = "{} Failed to decode JSON: {}".format(
                    self.get_invocation_id(), e
                )

                su.add_ucc_error_logger(
                    logger=self.logger,
                    logger_type=snow_consts.GENERAL_EXCEPTION,
                    exception=e,
                    msg_before=error_msg,
                )
                msg = "Invalid JSON response"
                return msg if error_only else {"Error Message": msg}
        elif isinstance(content, dict):
            resp = content
        else:
            self.logger.error(
                "{} Unexpected content type: {}".format(
                    self.get_invocation_id(), type(content)
                )
            )
            msg = "Unexpected response format"
            return msg if error_only else {"Error Message": msg}

        if resp.get("error"):
            self.logger.error(
                "{} Failed with error: {}".format(
                    self.get_invocation_id(), resp["error"]
                )
            )
            return resp["error"] if error_only else {"Error Message": resp["error"]}

        if resp.get("Error Message"):
            self.fail_count += 1
            return resp.get("Error Message") if error_only else resp

        if return_first:
            result = resp.get("result")
            if isinstance(result, list):
                if result and result[0].get("status", "") == "error":
                    error_msg = result[0].get("error_message", "Unknown error")
                    self.logger.error(
                        "{} Error Message: {}".format(
                            self.get_invocation_id(), error_msg
                        )
                    )
                    return error_msg if error_only else {"Error Message": error_msg}
                return result[0] if result else {}
            else:
                return resp.get("result")

        return resp

    def handle(self):
        """Wrapper over the _do_handle function"""
        try:
            return self._do_handle()
        except Exception as e:
            import sys

            msg = f"{self.get_invocation_id()} Error occured."
            su.add_ucc_error_logger(
                logger=self.logger,
                logger_type=snow_consts.GENERAL_EXCEPTION,
                exception=e,
                msg_before=msg,
            )
            # Exit to handle the new version of custom command execution
            # because NoneType object is not iterable.
            sys.exit(1)

    def _do_handle(self) -> list:
        """
        Handles the end-to-end processing of events to create or update records in ServiceNow.

        :return list: A list of processed results from successful event executions.
        """
        self.logger.info(
            "{} Start of _do_handle_record function".format(self.get_invocation_id())
        )

        self.fail_count = 0
        self.headers = {
            "Content-type": "application/json",
            "Accept": "application/json",
        }

        events_list = self._get_events()

        if not events_list:
            self.logger.info(
                "{} No events to process.".format(self.get_invocation_id())
            )
            return []

        total_events = len(events_list)
        self.logger.info(
            "{} Number of events to process: {}".format(
                self.get_invocation_id(), total_events
            )
        )

        self._update_headers_with_auth_details()
        self.proxy_info = su.build_proxy_info(self.snow_account)
        self.sslconfig = su.get_sslconfig(
            self.snow_account, self.session_key, self.logger
        )

        results = []
        with ThreadPoolExecutor(max_workers=20) as executor:
            future_to_event = {
                executor.submit(self.process_event, self._prepare_data(event)): event
                for event in events_list
                if event
            }

            for future in as_completed(future_to_event):
                raw_event = future_to_event[future]
                try:
                    result = future.result()
                    if result:
                        results.append((result, raw_event))
                    else:
                        self.fail_count += 1
                except Exception as e:
                    self.fail_count += 1
                    self.logger.error(
                        "{} Error in processing event. Exception: {}".format(
                            self.get_invocation_id(), traceback.format_exc()
                        )
                    )

        processed_results = self._process_results(results) if results else []

        if self.fail_count == 0:
            self.logger.info(
                f"{self.get_invocation_id()} Successfully created {len(processed_results)} tickets out of {total_events} events for account: {self.snow_account['account']}."
            )
        else:
            self.logger.error(
                f"{self.get_invocation_id()} Failed to create {self.fail_count} tickets out of {total_events} events for account: {self.snow_account['account']}."
            )
            splunk_rest.simpleRequest(
                "messages",
                self.session_key,
                postargs={
                    "severity": "error",
                    "name": f"ServiceNow error message - {int(time.time())}",
                    "value": f"Failed to create {self.fail_count} tickets out of {total_events} events for account: {self.snow_account['account']}.",
                },
                method="POST",
            )

        self.logger.info(
            f"{self.get_invocation_id()} End of _do_handle_record function"
        )

        return processed_results

    def process_event(self, event):
        """
        Processes a single event by executing the appropriate ServiceNow action with retry logic.

        :param event: A dictionary representing the event data to be processed.
        :return dict: The content of the ServiceNow API interaction for the given event.
        """
        self.logger.debug(f"{self.get_invocation_id()} Processing event")
        result = self._do_event(event, self.headers, retry=0)
        return result

    def _do_event(self, event_data, headers, retry=0):
        """
        Handles the execution of an event (record creation/update/query) in ServiceNow with retry logic and dynamic method handling.

        :param event_data: Dictionary containing the event and ServiceNow table configuration data.
        :param headers: Dictionary of HTTP headers for the request.
        :param retry: Retry count for the request in case of recoverable errors (default is 0).
        :return dict: A dictionary containing the result or error message from the ServiceNow API response.
        """
        snow_table_config = event_data.get("snow_table_config", {})
        method = snow_table_config.get("method", "POST").upper()
        subcommand = snow_table_config.get("subcommand", "create")
        sys_id = snow_table_config.get("sys_id")
        table = event_data.get("table_name")
        endpoint = self._build_endpoint(table, subcommand, sys_id)

        try:
            if retry > 0:
                self.logger.info(
                    "{} Retry count: {}/3".format(self.get_invocation_id(), retry + 1)
                )

            if method == "PUT" and not sys_id:
                msg = "{} Missing sys_id to update {}".format(
                    self.get_invocation_id(), table
                )
                self.logger.error(msg)
                return {"Error Message": "Missing sys_id to update the record"}

            if method == "GET":
                config = event_data["snow_table_config"]
                params = {
                    "sysparm_fields": "sys_id",
                    "sysparm_limit": 2,
                    **config.get("params", {}),
                }
                return self._handle_get(event_data, headers, endpoint, params, retry)

            # Handling POST/PUT call
            post_data = event_data.get("payload", {})
            self.logger.info(
                "{} Initiating {} request to {}".format(
                    self.get_invocation_id(), method, endpoint
                )
            )
            response = self._send_request(method, endpoint, headers, data=post_data)
            content = response.content

            results = self._handle_response(
                response, content, event_data, retry, method
            )
            if results.get("Error Message"):
                return results
            return results.get("content")

        except Exception as e:
            msg = "{} Failed request to {}, error={}".format(
                self.get_invocation_id(), endpoint, traceback.format_exc()
            )
            su.add_ucc_error_logger(
                logger=self.logger,
                logger_type=snow_consts.CONNECTION_ERROR,
                exception=e,
                msg_before=msg,
            )
            return {"Error Message": "Failed to create or update the record"}

    def _send_request(self, method, endpoint, headers, data=None, params=None):
        """
        Sends an HTTP request to the given ServiceNow endpoint using specified method, headers, and payload.

        :param method: HTTP method (e.g., 'GET', 'POST', 'PUT').
        :param endpoint: Target URL for the request.
        :param headers: HTTP headers to include in the request.
        :param data: Optional JSON data for POST/PUT requests.
        :param params: Optional query parameters for GET requests.
        :return requests.Response: The HTTP response object from the request.
        """
        return requests.request(
            method,
            endpoint,
            json=data if method in ["POST", "PUT"] else None,
            params=params if method == "GET" else None,
            headers=headers,
            proxies=self.proxy_info,
            timeout=120,
            verify=self.sslconfig,
        )

    def _handle_get(
        self, event_data, headers, endpoint, params: dict = {}, retry: int = 0
    ):
        """
        Handles GET requests for record existence checks and determines whether to retry as POST or PUT.

        :param event_data: Dictionary containing the event and ServiceNow table configuration data.
        :param headers: HTTP headers to use for the GET request.
        :param endpoint: Full URL endpoint for the GET request.
        :param params: Dictionary of query parameters to send with the GET request.
        :param retry: Current retry count for recursive retry logic.
        :return dict: Response content or error message from further execution of _do_event.
        """
        self.logger.info(
            f"{self.get_invocation_id()} Initiating GET request to {endpoint} with params {params}"
        )

        response = self._send_request("GET", endpoint, headers, params=params)
        content = response.content
        results = self._handle_response(response, content, event_data, retry, "GET")

        if results.get("Error Message"):
            return results

        resp = self._get_resp_record(results.get("content"))

        if resp and resp.get("Error Message"):
            return resp

        result = resp.get("result")
        config = event_data.get("snow_table_config", {})

        if result and len(result) == 1:
            sys_id = result[0].get("sys_id")
            if not sys_id:
                return {
                    "Error Message": "sys_id missing from GET response",
                    "status_code": response.status_code,
                    "error_content": result[0],
                }

            self.logger.info(
                "{} Unique record with sys_id {} found from ServiceNow endpoint "
                "{} to update".format(self.get_invocation_id(), sys_id, endpoint)
            )

            config.update({"method": "PUT", "subcommand": "update", "sys_id": sys_id})
        else:
            config.update({"method": "POST", "subcommand": "create"})
            self.logger.info(
                "{} Multiple or no records found for endpoint {} with params {}, "
                "falling back to POST".format(
                    self.get_invocation_id(), endpoint, params
                )
            )

        self.logger.info(
            f"{self.get_invocation_id()} Sending request with method {event_data['snow_table_config']['method']}"
        )
        return self._do_event(event_data, headers, retry=0)

    def _handle_retry_recursive_event_call(self, event_data, headers, retry) -> dict:
        """
        Handles the recursively invoking _do_event logic.

        :param event_data: Original request data including snow_table_config.
        :param headers:  HTTP headers to use for the request.
        :param retry: retry count.
        :param method: HTTP method used in the request (GET, POST, PUT).
        :return dict: Dictionary containing either the response content or an error message.
        """
        try:
            self.logger.debug(
                f"{self.get_invocation_id()} Handling retry recursive call"
            )
            do_response = self._do_event(event_data, headers, retry)
            if isinstance(do_response, bytes):
                return {"content": do_response}
            elif isinstance(do_response, dict):
                return do_response
            else:
                return {"Error Message": f"Unexpected result type: {type(do_response)}"}
        except Exception as e:
            return {"Error Message": str(e)}

    def _handle_response(
        self, response, content, event_data, retry, method=None
    ) -> dict:
        """
        Handles the HTTP response from ServiceNow and applies retry logic based on status code and auth type.

        :param response: HTTP response object from the request.
        :param content: Raw content of the response body.
        :param event_data: Original request data including snow_table_config.
        :param retry: retry count.
        :param method: HTTP method used in the request (GET, POST, PUT).
        :return dict: Dictionary containing either the response content or an error message and status code.
        """
        status_code = response.status_code

        if status_code in (200, 201):
            return {"content": content, "status_code": status_code}

        elif status_code == 400:
            self.logger.error(
                f"{self.get_invocation_id()} Failed to {method} record. Status: {status_code}. "
                f"Possible missing plugins. Content: {content}"
            )
            return {
                "Error Message": self._get_resp_record(content, False, True),
                "status_code": status_code,
                "error_content": content,
            }

        elif status_code == 401 and self.snow_account.get("auth_type") in [
            "oauth",
            "oauth_client_credentials",
        ]:
            self.logger.error(
                f"{self.get_invocation_id()} Auth failure during {method}. Status: {status_code}. Retrying with refreshed token."
            )
            if retry < 2 and self._regenerate_access_token():
                return self._handle_retry_recursive_event_call(
                    event_data, self.headers, retry + 1
                )
            return {
                "Error Message": self._get_resp_record(content, False, True),
                "status_code": status_code,
                "error_content": content,
            }

        else:
            self.logger.error(
                f"{self.get_invocation_id()} Failed to {method or 'create'} ticket. Status: {status_code}, Reason: {response.reason}"
            )
            if retry < 2:
                return self._handle_retry_recursive_event_call(
                    event_data, self.headers, retry + 1
                )
            return {
                "Error Message": self._get_resp_record(content, False, True),
                "status_code": status_code,
                "error_content": content,
            }

    def _update_headers_with_auth_details(self):
        """Update the headers details"""
        if self.snow_account["auth_type"] in ["oauth", "oauth_client_credentials"]:
            self.headers.update(
                {"Authorization": "Bearer %s" % self.snow_account["access_token"]}
            )
        else:
            credentials = base64.urlsafe_b64encode(
                (
                    f'{self.snow_account["username"]}:{self.snow_account["password"]}'
                ).encode("UTF-8")
            ).decode("ascii")
            self.headers.update({"Authorization": "Basic %s" % credentials})

    def _get_conf(self, conf_name: str):
        """
        Get the sepecific conf file information

        :param conf_name: conf file name to get
        :return: Return conf information
        """
        cfm = conf_manager.ConfManager(
            self.session_key,
            snow_consts.APP_NAME,
            realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(
                snow_consts.APP_NAME, conf_name
            ),
        )
        return cfm.get_conf(f"{conf_name}").get_all()

    def _get_service_now_account(self):
        """
        This function is used read config files
        :return: snow_account dictionary
        """

        snow_account = {
            "session_key": self.session_key,
            "app_name": op.basename(op.dirname(op.dirname(op.abspath(__file__)))),
        }
        account_access_fields = [
            "username",
            "password",
            "client_id",
            "client_secret",
            "client_id_oauth_credentials",
            "client_secret_oauth_credentials",
            "access_token",
            "refresh_token",
            "auth_type",
        ]

        try:
            # Read account details from conf file
            splunk_ta_snow_account_conf = self._get_conf("splunk_ta_snow_account")
            self.logger.info(
                "Getting details for account '{}'".format(
                    self.account  # pylint: disable=E1101
                )
            )

            if not self.account:  # pylint: disable=E1101
                msg = (
                    "Account name cannot be empty. Enter a configured account name or "
                    "create new account by going to Configuration page of the Add-on."
                )
                self._write_error(msg, True)

            # Get account details
            elif self.account in splunk_ta_snow_account_conf:  # pylint: disable=E1101
                account_details = splunk_ta_snow_account_conf[
                    self.account  # pylint: disable=E1101
                ]

                snow_account["account"] = self.account  # pylint: disable=E1101
                prefix = re.search("^https?://", account_details["url"])
                if not prefix:
                    snow_account["url"] = "https://{}".format(account_details["url"])
                else:
                    snow_account["url"] = account_details["url"]

                if not snow_account["url"].endswith("/"):
                    snow_account["url"] = "{}/".format(snow_account["url"])

                snow_account[
                    "disable_ssl_certificate_validation"
                ] = account_details.get("disable_ssl_certificate_validation", 0)

                account_auth_type = account_details.get("auth_type", "basic")

                if account_auth_type not in [
                    "basic",
                    "oauth",
                    "oauth_client_credentials",
                ]:
                    msg = (
                        "'{}' is not configured with the desired authentication type. Expected "
                        "values are 'basic', 'oauth' and 'oauth_client_credentials'. Current value is '{}'".format(
                            self.account, account_auth_type  # pylint: disable=E1101
                        )
                    )
                    self._write_error(msg, True)

                snow_account["auth_type"] = account_auth_type

                # Collecting details of account
                for field in account_access_fields:
                    if field in account_details.keys():
                        if (
                            field in ["password"]
                            and account_details.get("auth_type", "basic") == "basic"
                        ):
                            snow_account[field] = (
                                account_details[field]
                                .encode("ascii", "replace")
                                .decode("ascii")
                            )
                        elif (
                            field
                            in [
                                "client_id",
                                "client_secret",
                                "access_token",
                                "refresh_token",
                            ]
                            and account_details.get("auth_type", "basic") == "oauth"
                        ):
                            snow_account[field] = (
                                account_details[field]
                                .encode("ascii", "replace")
                                .decode("ascii")
                            )
                        elif (
                            field
                            in [
                                "client_id_oauth_credentials",
                                "client_secret_oauth_credentials",
                                "access_token",
                            ]
                            and account_details.get("auth_type", "basic")
                            == "oauth_client_credentials"
                        ):
                            snow_account[field] = (
                                account_details[field]
                                .encode("ascii", "replace")
                                .decode("ascii")
                            )
                        else:
                            snow_account[field] = account_details[field]

            # Invalid account name
            else:
                msg = (
                    "'"
                    + self.account  # pylint: disable=E1101
                    + "' is not configured. Enter a configured account name or create "
                    "new account by going to Configuration page of the Add-on."
                )
                self._write_error(msg, True)

            # Read log and proxy setting details from conf file
            splunk_ta_snow_setting_conf = self._get_conf("splunk_ta_snow_settings")

            if utils.is_true(
                splunk_ta_snow_setting_conf["proxy"].get("proxy_enabled", False)
            ):
                snow_account["proxy_enabled"] = splunk_ta_snow_setting_conf["proxy"][
                    "proxy_enabled"
                ]
                if splunk_ta_snow_setting_conf["proxy"].get("proxy_port"):
                    snow_account["proxy_port"] = int(
                        splunk_ta_snow_setting_conf["proxy"]["proxy_port"]
                    )
                if splunk_ta_snow_setting_conf["proxy"].get("proxy_url"):
                    snow_account["proxy_url"] = splunk_ta_snow_setting_conf["proxy"][
                        "proxy_url"
                    ]
                if splunk_ta_snow_setting_conf["proxy"].get("proxy_username"):
                    snow_account["proxy_username"] = splunk_ta_snow_setting_conf[
                        "proxy"
                    ]["proxy_username"]
                if splunk_ta_snow_setting_conf["proxy"].get("proxy_password"):
                    snow_account["proxy_password"] = splunk_ta_snow_setting_conf[
                        "proxy"
                    ]["proxy_password"]
                if splunk_ta_snow_setting_conf["proxy"].get("proxy_type"):
                    snow_account["proxy_type"] = splunk_ta_snow_setting_conf["proxy"][
                        "proxy_type"
                    ]
                if splunk_ta_snow_setting_conf["proxy"].get("proxy_rdns"):
                    snow_account["proxy_rdns"] = splunk_ta_snow_setting_conf["proxy"][
                        "proxy_rdns"
                    ]

            if "loglevel" in list(splunk_ta_snow_setting_conf["logging"].keys()):
                snow_account["loglevel"] = splunk_ta_snow_setting_conf["logging"][
                    "loglevel"
                ]

            return snow_account
        except Exception as e:
            error_msg = str(traceback.format_exc())
            if "splunk_ta_snow_account does not exist." in error_msg:
                msg = (
                    "No ServiceNow account configured. "
                    "Configure account by going to Configuration page of the Add-on."
                )
                self._write_error(msg, True)
            else:
                self._write_error("{} Exception: {}".format(e), True)

    def _regenerate_access_token(self):
        """Regenerate the access token"""
        with self.token_lock:
            if self.snow_account.get("token_expiry", time.time() - 1) > time.time() + 1:
                return True
            self.logger.info(
                f"{self.get_invocation_id()} [{threading.current_thread().name}] generating new access token"
            )
            snow_oauth = soauth.SnowOAuth(self.snow_account, self._get_log_file())
            update_status, token_expiry = snow_oauth.regenerate_oauth_access_tokens()

            # If access token is updated successfully, retry record creation
            if update_status:
                self.snow_account = self._get_service_now_account()
                self.headers.update(
                    {"Authorization": "Bearer %s" % self.snow_account["access_token"]}
                )
                self.sslconfig = su.get_sslconfig(
                    self.snow_account, self.session_key, self.logger
                )
                self.snow_account["token_expiry"] = time.time() + token_expiry
                return True
            else:
                self.logger.error(
                    f"{self.get_invocation_id()} Unable to regenerate new access token. Failure potentially caused by "
                    "the expired refresh token. To fix the issue, reconfigure the account and try again."
                )
                return False
