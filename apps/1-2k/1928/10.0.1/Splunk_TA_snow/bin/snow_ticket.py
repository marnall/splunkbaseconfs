#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test  # isort: skip # noqa: F401
import argparse
import base64
import csv
import gzip
import json
import os.path as op
import queue
import re
import sys
import time
import traceback

import requests
import snow_consts
import snow_oauth_helper as soauth
import snow_utility as su

from splunk import rest as splunk_rest
import splunk.Intersplunk as si
import threading
from multiprocessing.pool import ThreadPool
from solnlib import conf_manager, utils, log


utils.remove_http_proxy_env_vars()


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        si.parseError("{0}. {1}".format(message, self.format_usage()))


class ICaseDictReader(csv.DictReader, object):
    @property
    def fieldnames(self):
        return [
            field.strip().lower() for field in super(ICaseDictReader, self).fieldnames
        ]


class SnowTicket(object):
    def __init__(self):
        self.session_key = self._get_session_key()
        if not hasattr(self, "invocation_id"):
            self.invocation_id = ""
        self.logger = su.create_log_object(self._get_log_file())
        self.snow_account = self._get_service_now_account()
        self.subcommand = "create"
        self.sys_id = None
        self.token_lock = threading.RLock()

    def get_invocation_id(self):
        return "[invocation_id={}]".format(self.invocation_id)

    def _get_session_key(self):
        """
        When called as custom search script, splunkd feeds the following
        to the script as a single line
        'authString:<auth><userId>admin</userId><username>admin</username>\
            <authToken><32_character_long_uuid></authToken></auth>'

        When called as an alert callback script, splunkd feeds the following
        to the script as a single line
        sessionKey=31619c06960f6deaa49c769c9c68ffb6
        """

        import urllib.parse

        session_key = sys.stdin.readline()
        m = re.search("authToken>(.+)</authToken", session_key)
        if m:
            session_key = m.group(1)
        else:
            session_key = session_key.replace("sessionKey=", "").strip()
        session_key = urllib.parse.unquote(session_key.encode("ascii").decode("ascii"))
        session_key = session_key.encode().decode("utf-8")
        return session_key

    def handle(self):
        try:
            msg = self._do_handle()
            if msg and msg.get("Error Message"):
                si.parseError(msg.get("Error Message"))
        except Exception as e:
            msg = f"{self.get_invocation_id()} Error occured."
            su.add_ucc_error_logger(
                logger=self.logger,
                logger_type=snow_consts.GENERAL_EXCEPTION,
                exception=e,
                msg_before=msg,
            )

    def _do_handle(self):
        self.logger.info(f"{self.get_invocation_id()} Start of _do_handle function")

        self.results = queue.Queue()
        pool = ThreadPool(20)
        self.fail_count = 0
        self.headers = {
            "Content-type": "application/json",
            "Accept": "application/json",
        }
        events_list = self._get_events()
        if events_list:
            total_events = len(events_list)
            self.endpoint = self._get_event_endpoint(events_list[0])
            self._update_headers_with_auth_details()
            self.proxy_info = su.build_proxy_info(self.snow_account)
            self.sslconfig = su.get_sslconfig(
                self.snow_account, self.session_key, self.logger
            )
            for event in events_list:
                if event is not None:
                    event_data = self._prepare_event_data(event)
                    pool.apply_async(
                        self.process_event,
                        args=(event_data,),
                        callback=self._handle_result,
                    )
            pool.close()
            pool.join()

            if self.results:
                processed_results = self._process_results()
                if processed_results:
                    if self.fail_count == 0:
                        self.logger.info(
                            f"{self.get_invocation_id()} Successfully created {len(processed_results)} tickets out of {total_events} events for account: {self.snow_account['account']}."
                        )
                    si.outputResults(processed_results)

            if self.fail_count:
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

        self.logger.info(f"{self.get_invocation_id()} End of _do_handle function")
        return None

    def _process_results(self):
        processed_results = []
        while not self.results.empty():
            content = self.results.get(timeout=5)
            resp = self._get_resp_record(content)
            if not resp:
                self.fail_count += 1
                continue
            if "Error Message" in resp:
                processed_results.append(resp)
            else:
                result = self._get_result(resp)
                result["_time"] = time.time()
                processed_results.append(result)

        return processed_results

    def _get_event_endpoint(self, event):
        scripted_endpoint = event.get("scripted_endpoint")
        if (
            scripted_endpoint
            and scripted_endpoint
            != "/api/now/table/x_splu2_splunk_ser_u_splunk_incident"
        ):
            endpoint = event["scripted_endpoint"]
            self.scripted_endpoint = event["scripted_endpoint"]
        else:
            endpoint = self._get_endpoint()
        endpoint = "{0}{1}".format(self.snow_account["url"], endpoint.lstrip("/"))
        return endpoint

    def _update_headers_with_auth_details(self):
        # Adding access_token in the headers if auth_type = oauth
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

    def _regenerate_access_token(self):
        with self.token_lock:
            if self.snow_account.get("token_expiry", time.time() - 1) > time.time() + 1:
                return True
            self.logger.info(
                f"{self.get_invocation_id()} [{threading.current_thread().name}] generating new access token"
            )
            snow_oauth = soauth.SnowOAuth(self.snow_account, self._get_log_file())
            update_status, token_expiry = snow_oauth.regenerate_oauth_access_tokens()

            # If access token is updated successfully, retry incident/event creation
            if update_status:
                # Updating the values in self.snow_account variable with the latest tokens
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

    def _prepare_event_data(self, event):
        event_data = self._prepare_data(event)
        if not event_data:
            self.logger.info(f"{self.get_invocation_id()} No event data is available")
            return
        if event_data.get("Error Message"):
            return event_data

        event_data = json.dumps(event_data)
        return event_data

    def _handle_result(self, result):
        if result:
            self.results.put(result)
        else:
            self.fail_count += 1

    def process_event(self, event):
        # Process each event
        # Log the current thread processing the event
        self.logger.debug(
            f"{self.get_invocation_id()} [{threading.current_thread().name}] Processing event"
        )

        self.logger.debug(
            "{} Sending request to {}: {}".format(
                self.get_invocation_id(), self.endpoint, event
            )
        )
        result = self._do_event(event, self.headers, retry=0)
        return result

    def _do_event(self, event_data, headers, retry=0):
        # This function will be re-executed if oauth access token will be regenerated
        # session_key = self.snow_account["session_key"]
        if retry > 0:
            self.logger.info(
                "{} Retry count: {}/3".format(self.get_invocation_id(), retry + 1)
            )
        self.logger.info(
            "{} Initiating request to {}".format(
                self.get_invocation_id(), self.endpoint
            )
        )
        try:
            # semgrep ignore reason: we have custom handling for unsuccessful HTTP status codes
            response = requests.request(  # nosemgrep: python.requests.best-practice.use-raise-for-status.use-raise-for-status  # noqa: E501
                self._get_http_method(),
                self.endpoint,
                data=event_data,
                headers=headers,
                proxies=self.proxy_info,
                timeout=120,
                verify=self.sslconfig,
            )
            content = response.content
            self.logger.info(
                "{} Sending request to {}, get response code {}".format(
                    self.get_invocation_id(), self.endpoint, response.status_code
                )
            )
            result = self._handle_response(response, content, event_data, retry)
            self.logger.info(
                "{} Ending request to {}".format(
                    self.get_invocation_id(), self.endpoint
                )
            )
            # Since the access token is updated in the configuration file, we will retry the incident/event creation
            return result
        except Exception as e:
            msg = "{} Failed to connect to {}, error={}".format(
                self.get_invocation_id(), self.endpoint, traceback.format_exc()
            )
            su.add_ucc_error_logger(
                logger=self.logger,
                logger_type=snow_consts.CONNECTION_ERROR,
                exception=e,
                msg_before=msg,
            )
            return {"Error Message": "Failed to create ticket."}

    def _get_endpoint(self):
        if self.subcommand == "create":
            return f"api/now/table/{self._get_table()}"
        else:
            return f"api/now/table/{self._get_table()}/{self.sys_id}"

    def _get_http_method(self):
        if self.subcommand == "update":
            return "PUT"
        else:
            return "POST"

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
            account_cfm = conf_manager.ConfManager(
                self.session_key,
                snow_consts.APP_NAME,
                realm="__REST_CREDENTIAL__#{}#configs/conf-splunk_ta_snow_account".format(
                    snow_consts.APP_NAME
                ),
            )
            splunk_ta_snow_account_conf = account_cfm.get_conf(
                "splunk_ta_snow_account"
            ).get_all()
            self.logger.info(
                "Getting details for account '{}'".format(
                    self.account  # pylint: disable=E1101
                )
            )

            # Check if account is empty
            if not self.account:  # pylint: disable=E1101
                si.generateErrorResults("Enter ServiceNow account name.")
                raise Exception(
                    "Account name cannot be empty. Enter a configured account name or "
                    "create new account by going to Configuration page of the Add-on."
                )
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
                    si.generateErrorResults(
                        "'{}' is not configured with the desired authentication type. Expected "
                        "values are 'basic', 'oauth' and 'oauth_client_credentials'. Current value is '{}'".format(
                            self.account, account_auth_type  # pylint: disable=E1101
                        )
                    )
                    raise Exception(
                        "'{}' is not configured with the desired authentication type. Expected "
                        "values are 'basic', 'oauth' and 'oauth_client_credentials'. Current value is '{}'".format(
                            self.account, account_auth_type  # pylint: disable=E1101
                        )
                    )

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
                si.generateErrorResults(
                    "'"
                    + self.account  # pylint: disable=E1101
                    + "' is not configured. Enter a configured account name or create "
                    "new account by going to Configuration page of the Add-on."
                )
                raise Exception(
                    "Entered ServiceNow account name is invalid. Enter a configured account name or "
                    "create new account by going to Configuration page of the Add-on."
                )

            # Read log and proxy setting details from conf file
            setting_cfm = conf_manager.ConfManager(
                self.session_key,
                snow_consts.APP_NAME,
                realm="__REST_CREDENTIAL__#{}#configs/conf-splunk_ta_snow_settings".format(
                    snow_consts.APP_NAME
                ),
            )
            splunk_ta_snow_setting_conf = setting_cfm.get_conf(
                "splunk_ta_snow_settings"
            ).get_all()

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
                si.generateErrorResults(
                    "No ServiceNow account configured. "
                    "Configure account by going to Configuration page of the Add-on."
                )
                msg = (
                    f"No ServiceNow account configured. "
                    "Configure account by going to Configuration page of the Add-on.\n"
                    + traceback.format_exc()
                )
                su.add_ucc_error_logger(
                    logger=self.logger,
                    logger_type=snow_consts.GENERAL_EXCEPTION,
                    exception=e,
                    msg_before=msg,
                )
            else:
                su.add_ucc_error_logger(
                    logger=self.logger,
                    logger_type=snow_consts.GENERAL_EXCEPTION,
                    exception=e,
                )

    def _prepare_data(self, event):
        """
        Return a dict like object
        """
        return event

    def _get_events(self):
        """
        Return events that need to be handled
        """
        raise NotImplementedError("Derive class shall implement this method.")

    def _get_log_file(self) -> str:
        """
        Return the log file name
        """
        return "splunk_ta_snow_ticket"

    def _handle_response(self, response, content, event_data, retry):
        status_code = response.status_code
        if status_code in (200, 201):
            return content
        elif status_code == 400:
            self.logger.error(
                "{0} Failed to create ticket. Return code is {1} ({2}). One of the possible causes of "
                "failure is absence of event management plugin or Splunk Integration plugin on the "
                "ServiceNow instance. To fix the issue install the plugin(s) on ServiceNow "
                "instance.".format(
                    self.get_invocation_id(), status_code, response.reason
                )
            )
            return None
        elif status_code == 401 and self.snow_account["auth_type"] in [
            "oauth",
            "oauth_client_credentials",
        ]:
            self.logger.error(
                "{0} Failed to create ticket. Return code is {1} ({2}). Failure potentially caused by "
                " expired access token. Regenerating access token.".format(
                    self.get_invocation_id(), status_code, response.reason
                )
            )
            if (retry < 2) and self._regenerate_access_token():
                return self._do_event(event_data, self.headers, retry + 1)
            return None
        else:
            self.logger.error(
                "{0} Failed to create ticket. Return code is {1} ({2}).".format(
                    self.get_invocation_id(), status_code, response.reason
                )
            )
            if retry < 2:
                return self._do_event(event_data, self.headers, retry + 1)
            return None

    def _handle_error(self, msg="Failed to create ticket."):
        si.parseError(msg)

    def _get_ticket_link(self, sys_id):
        link = "{0}{1}.do?sysparm_query=sys_id={2}".format(
            self.snow_account["url"], self._get_table(), sys_id
        )
        return link

    def _get_resp_record(self, content):
        if isinstance(content, bytes):
            content = content.decode("utf-8")

        if isinstance(content, str):
            try:
                resp = json.loads(content)
            except json.JSONDecodeError as e:
                self.logger.error(
                    f"{self.get_invocation_id()} Failed to decode JSON: {e}"
                )
                return {"Error Message": "Invalid JSON response"}
        elif isinstance(content, dict):
            resp = content
        else:
            self.logger.error(
                f"{self.get_invocation_id()} Unexpected content type: {type(content)}"
            )
            return {"Error Message": "Unexpected response format"}

        if resp.get("error"):
            self.logger.error(
                "{} Failed with error: {}".format(
                    self.get_invocation_id(), resp["error"]
                )
            )
            return None

        if resp.get("Error Message"):
            self.fail_count += 1
            return resp

        if (
            isinstance(resp.get("result"), list)
            and resp.get("result", [{}])[0].get("status", "") == "error"
        ):
            self.logger.error(
                "{} Error Message: {}".format(
                    self.get_invocation_id(), resp.get("result")[0].get("error_message")
                )
            )
            return {"Error Message": resp.get("result")[0].get("error_message")}
        if isinstance(resp.get("result"), list):
            return resp["result"][0]
        return resp.get("result")

    def _get_result(self, resp):
        """
        Return a dict object
        """
        raise NotImplementedError("Derived class shall overrides this")

    def _get_table(self):
        """
        Return a table name
        """
        raise NotImplementedError("Derived class shall overrides this")

    def _get_failure_message(self):
        """
        Implement this method to get custom error messages
        Return custom error message in dict form {'error': 'error message'}
        """
        return None


def read_alert_results(alert_file, logger, invocation_id):
    logger.info("{} Reading alert file {}".format(invocation_id, alert_file))
    if not op.exists(alert_file):
        logger.error(
            "{} Unable to find the file {}. Contact Splunk administrator for further information.".format(
                invocation_id, alert_file
            )
        )
        yield None
    with gzip.open(alert_file, "rt") as f:
        for event in ICaseDictReader(f, delimiter=","):
            yield event


def get_account(alert_file):
    """
    This function is used to identify account for alert actions
    :param alert_file: file name
    :return: account name
    """
    try:
        logger = su.create_log_object("splunk_ta_snow_ticket")
        if not op.exists(alert_file):
            logger.error(
                "Unable to find the file {}. Contact Splunk administrator for further information.".format(
                    alert_file
                )
            )

        with gzip.open(alert_file, "rt") as f:
            for event in ICaseDictReader(f, delimiter=","):
                return event.get("account")
    except Exception as e:
        su.add_ucc_error_logger(
            logger=logger,
            logger_type=snow_consts.GENERAL_EXCEPTION,
            exception=e,
        )
