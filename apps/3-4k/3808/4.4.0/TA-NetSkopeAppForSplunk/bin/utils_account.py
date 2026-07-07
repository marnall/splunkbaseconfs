"""Utilities related to account page."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(__file__, "..", "common")))

import ta_netskopeappforsplunk_declare  # noqa: F401

import api.netskope_v2.client
import api.netskope_v1.client

from modinputs.iterator.handle_iterator_api_calls import DataUtils

import sys
import time
import netskope_utils
import socks
import requests
import concurrent.futures
import six
import splunk.admin as admin
import const
import re

from os import path
from requests.exceptions import RequestException
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from splunktaucclib.rest_handler.endpoint import SingleModel
from splunktaucclib.rest_handler.endpoint.validator import Validator
from splunktaucclib.rest_handler.error import RestError
from netskope_utils import GetSessionKey, read_conf_file

from splunk.clilib.bundle_paths import make_splunkhome_path

from ta_netskopeappforsplunk.netskope_iterator_sdk.netskope_api.iterator.netskope_iterator import (
    NetskopeIterator,
)  # noqa: E402,E501
from ta_netskopeappforsplunk.netskope_iterator_sdk.netskope_api.iterator.const import Const  # noqa: E402

BAD_REQUEST_STATUS_CODE = 400
ACCOUNT_STANZA_NAME = None
MAX_RETRY = 3

# Static stanzax for all netskope inputs
NETSKOPE_INPUTS = {
    "netskope_events_v2": {
        "interval": const.ITERATOR_INTERVAL_SEC,
        "timeout": const.EVENTS_TIMEOUT,
        "start_datetime": netskope_utils.get_default_datetime(last_days=const.ITERATOR_DEFAULT_STARTDATETIME_DAYS_BACK),
        "disabled": "true",
    },
    "netskope_alerts_v2": {
        "timeout": const.ALERTS_TIMEOUT,
        "interval": const.ITERATOR_INTERVAL_SEC,
        "start_datetime": netskope_utils.get_default_datetime(last_days=const.ITERATOR_DEFAULT_STARTDATETIME_DAYS_BACK),
        "disabled": "true",
    },
    "netskope_events_multi_iterator": {
        "timeout": const.EVENTS_TIMEOUT,
        "interval": const.ITERATOR_INTERVAL_SEC,
        "disabled": "true",
    },
    "netskope_events_v2_csv": {
        "interval": const.ITERATOR_INTERVAL_SEC,
        "timeout": const.EVENTS_TIMEOUT,
        "disabled": "true",
    },
    "netskope_alerts_v2_csv": {
        "timeout": const.ALERTS_TIMEOUT,
        "interval": const.ITERATOR_INTERVAL_SEC,
        "disabled": "true",
    },
    "netskope_clients": {
        "sourcetype": "netskope:clients",
        "disabled": "true",
        "start_datetime": netskope_utils.get_default_datetime(),
        "failed_window_retries": const.FAILED_WINDOW_RETRIES,
    },
    "netskope_clients_iterator": {
        "sourcetype": "netskope:clientstatus",
        "timeout": const.CLIENTS_TIMEOUT,
        "interval": const.ITERATOR_INTERVAL_SEC,
        "disabled": "true",
    },
    "netskope_webtransactions": {"sourcetype": "netskope:web_transaction", "disabled": "true"},
    "netskope_webtransactions_v2": {"sourcetype": "netskope:web_transaction", "disabled": "true"},
}

# Input type to Modular Input Name mapping
INPUT_MAPPING = {
    "alerts_v2": "netskope_alerts_v2",
    "events_v2": "netskope_events_v2",
    "clients": "netskope_clients",
    "web_transactions_v2": "netskope_webtransactions_v2",
}

SPLUNK_HOME = "$SPLUNK_HOME"
BATCH_STANZA_V1 = path.join(SPLUNK_HOME, "var", "spool", "splunk", "{}*.gz")
CSV_FILE_PATH = make_splunkhome_path(["etc", "apps", "TA-NetSkopeAppForSplunk", "lookups", const.FILE_NAME])
if os.path.exists(CSV_FILE_PATH):
    BATCH_STANZA_V2 = path.join(SPLUNK_HOME, "var", "spool", "splunk", "webtxn1", "{}*.txt")
else:
    BATCH_STANZA_V2 = path.join(SPLUNK_HOME, "var", "spool", "splunk", "webtxn1", "{}*.gz")


class AccountModel(SingleModel):
    """Account Model."""

    def validate(self, name, data, existing=None):
        """To get stanza name for future use as it can only be retrive from here."""
        global ACCOUNT_STANZA_NAME
        ACCOUNT_STANZA_NAME = name

        hostname = data.get("hostname")
        token = data.get("token")
        token_v2 = data.get("token_v2")

        hostname_not_exists = (not hostname) or (isinstance(hostname, six.string_types) and len(hostname.strip()) <= 0)
        token_not_exists = (not token) or (isinstance(token, six.string_types) and len(token.strip()) <= 0)
        token_v2_not_exists = (not token_v2) or (isinstance(token_v2, six.string_types) and len(token_v2.strip()) <= 0)

        if hostname_not_exists:
            raise RestError(
                BAD_REQUEST_STATUS_CODE, "Hostname is required. Please enter Hostname."
            )

        if token_not_exists and token_v2_not_exists:
            raise RestError(
                BAD_REQUEST_STATUS_CODE, "Either Token V1 or Token V2 is required. Please enter the Token."
            )

        super(AccountModel, self).validate(name, data, existing)


class AccountHandler(ConfigMigrationHandler):
    """Account Handler."""

    def handleCreate(self, conf_info):
        """Handle creation of account in config file."""
        super(AccountHandler, self).handleCreate(conf_info)

    def handleRemove(self, conf_info):
        """Handle the delete operation."""
        session_key = GetSessionKey().session_key
        inputs_file = read_conf_file(session_key, "inputs")
        created_inputs = list(inputs_file.keys())
        input_list = []
        for each in created_inputs:
            each_netskope_input = each.split("://")
            if each.startswith("{}://".format(each_netskope_input[0])):
                configured_account = inputs_file.get(each).get("global_account")
                if configured_account == self.callerArgs.id:
                    input_list.append(each_netskope_input[1])
        if len(input_list) > 0:
            raise admin.ArgValidationException(
                "Account will not be deleted because it is linked with the \
                 following inputs: {}".format(
                    ", ".join(input_list)
                )
            )
        else:
            super(ConfigMigrationHandler, self).handleRemove(conf_info)


class TokenV2Validator(Validator):
    """To Validate Token of Netskope Account."""

    def validate(self, value, data):
        """Validate Netskope token given by user."""
        token = data.get("token_v2")
        hostname = data.get("hostname")
        try:
            if (not token) or (isinstance(token, six.string_types) and len(token.strip()) <= 0):
                # It is optional field.
                return True
            # Validate waterfall and iterator endpoint and if anyone respond success then it will allow.
            validation1, msg1 = token_v2_validator_waterfall(hostname, token)

            if not validation1:
                validation2, msg2 = token_v2_validator_iterator(hostname, token, True, ["audit"])
                if not validation2:
                    self.put_msg("Account validation error: {} | {}".format(msg1, msg2))
                    return False

        except Exception as ex:
            self.put_msg("Unexpected Error occured while validating Token V2 parameter: {}".format(ex))
            return False

        return True


def token_v2_validator_waterfall(hostname, token):
    """Validate the v2 token for waterfall input."""
    try:
        params = {"limit": 1, "skip": 0, "timeperiod": 3600}
        proxies = netskope_utils.create_requests_proxy_dict()
        timeout = 120
        api_client = api.netskope_v2.client.NetskopeAPIClient(hostname, token, timeout, proxies, retries=0)
        api_client.page_events.get(params=params)

    except (requests.exceptions.ProxyError, socks.ProxyError):
        message = "Invalid Proxy credentials. Please recheck your Proxy settings."
        return False, message

    except RequestException as ex:
        if ex.response is not None and ex.response.status_code == 401:
            message = "Could not connect to provided Netskope Account. "
            "Please recheck Netskope credentials or Proxy settings."
            return False, message

        message = "Could not connect to provided Netskope Account: {}".format(ex)
        return False, message

    except Exception as ex:
        message = "Error occured while validating Token V2 parameter: {}".format(ex)
        return False, message

    return True, "success"


def make_rest_call(hostname, token, is_event, _types, is_csv_input):
    """Do the API call to validate the selected event/alert type permissions."""
    retry_count = 0
    while retry_count <= MAX_RETRY:
        try:
            if _types == "connection":
                _types = "page"
            if _types == "All":
                _types = "Alert"
            res = None
            message = None
            params = {
                Const.NSKP_TOKEN: token,
                Const.NSKP_TENANT_HOSTNAME: hostname,
                Const.NSKP_EVENT_TYPE: _types if is_event else "alert",
                Const.NSKP_PROXIES: netskope_utils.create_requests_proxy_dict(),
                Const.NSKP_USER_AGENT: netskope_utils.get_user_agent(hostname, session_key=GetSessionKey().session_key),
                Const.NSKP_ALERT_TYPE: None if is_event or _types == "Alert" else _types,
            }

            if is_csv_input:
                _types = "alert" if _types == "Alert" else _types
                params[Const.NSKP_ITERATOR_NAME] = "stream_" + _types + "_logs"
                iterator = NetskopeIterator(params)
                res = iterator.tail()
                if res.headers.get("Schema_headers"):
                    res.raise_for_status()
                else:
                    message = (
                        "CSV format is not supported for this tenant. "
                        "Please contact Netskope Account team for enabling this feature."
                    )
            else:
                params[Const.NSKP_ITERATOR_NAME] = "splunk_" + "iterator_validation_" + _types
                iterator = NetskopeIterator(params)
                res = iterator.download(int(time.time()))
                res.raise_for_status()

        except (requests.exceptions.ProxyError, socks.ProxyError) as ex:
            message = "Please recheck your Proxy settings. Error: {}".format(str(ex))
        except requests.exceptions.HTTPError as ex:
            if res.status_code == 401:
                message = "Invalid creds. Please recheck Netskope credentials or Proxy settings."
            elif res.status_code == 403:
                message = "Token V2 has insufficient dataexport endpoint permissions."
            elif res.status_code == 429 or (res.status_code >= 500 and res.status_code < 600):
                if retry_count < MAX_RETRY:
                    retry_count += 1
                    continue
                elif res.status_code == 429:
                    message = "Too many requests: 429 Status code recieved for {}".format(str(ex))
                elif res.status_code >= 500 and res.status_code < 600:
                    message = "Received {} Status code. {}".format(
                        res.status_code,
                        str(ex)
                    )
            else:
                message = "Could not connect to provided Netskope Account. Status Code: {} Response: {}".format(
                    res.status_code, res.text
                )
        except Exception as ex:
            message = "Error occured while validating Token V2 parameter. Error: {}".format(str(ex))
        break

    return message, _types


def token_v2_validator_iterator(hostname, token, is_event, endpoint_types, is_csv_input=False):
    """Validate the v2 token for iterator inputs."""
    err_msgs = {}
    validation_msg = "success"
    type_mapping = {
        "compromisedcredential": "Compromised Credential",
        "ctep": "CTEP",
        "dlp": "DLP",
        "malsite": "Malsite",
        "malware": "Malware",
        "policy": "Policy",
        "quarantine": "Quarantine",
        "remediation": "Remediation",
        "securityassessment": "Security Assessment",
        "uba": "UBA",
        "watchlist": "Watchlist",
        "device": "Device",
        "content": "Content",
        "Alert": "All Alerts",
        "page": "Connection",
        "audit": "Audit",
        "application": "Application",
        "infrastructure": "Infrastructure",
        "network": "Network",
        "incident": "Incident",
        "endpoint": "Endpoint"
    }

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(endpoint_types)) as executor:
        future_to_res = {
            executor.submit(
                make_rest_call,
                hostname,
                token,
                is_event,
                _types,
                is_csv_input
            ): _types for _types in endpoint_types
        }
        for future in concurrent.futures.as_completed(future_to_res):
            try:
                message, _types = future.result()
                if message:
                    if message in err_msgs:
                        err_msgs.get(message).append(type_mapping.get(_types))
                    else:
                        err_msgs[message] = [type_mapping.get(_types)]
            except Exception:
                pass
    if len(err_msgs) > 0:
        validation_msg = ""
        for msg in err_msgs:
            validation_msg += "[" + " | ".join(err_msgs[msg]) + "] => " + msg + " "
        return False, validation_msg
    return True, validation_msg


class TokenValidator(Validator):
    """To Validate Token of Netskope Account."""

    def validate(self, value, data):
        """Validate Netskope token given by user."""
        token = data.get("token")
        hostname = data.get("hostname")
        try:
            if (not token) or (isinstance(token, six.string_types) and len(token.strip()) <= 0):
                # It is optional field.
                return True

            proxies = netskope_utils.create_requests_proxy_dict()
            payload = {"timeperiod": 3600, "limit": 1, "skip": 0}

            timeout = 120
            api_client = api.netskope_v1.client.NetskopeAPIClient(hostname, token, timeout, proxies, retries=0)
            api_client.clients.get(params=payload)

        except (requests.exceptions.ProxyError, socks.ProxyError):
            self.put_msg("Invalid Proxy credentials. Please recheck your Proxy settings.")
            return False

        except RequestException as ex:
            if ex.response is not None and ex.response.status_code == 401:
                self.put_msg(
                    "{} {}".format(
                        "Could not connect to provided Netskope Account.",
                        "Please recheck Netskope credentials or Proxy settings.",
                    )
                )
                return False

            self.put_msg("Could not connect to provided Netskope Account: {}".format(self.mask_sensitive_info(str(ex))))
            return False

        except Exception as ex:
            self.put_msg("Error occured while validating token parameter: {}".format(self.mask_sensitive_info(str(ex))))
            return False

        return True

    def mask_sensitive_info(self, message):
        """Mask the sensitive info in given message."""
        return re.sub(r"token=[^ \n]*", "token=<api_token>", message)


def make_rest_call_iterator(hostname, token, _types, iterator_name):
    """Do the API call to validate the selected Iterator type permissions."""
    if _types == "connection":
        _types = "page"
    message = None
    netskope_iterator_name = None
    headers = {"Netskope-Api-Token": token}
    params = {"eventtype": _types}
    proxies = netskope_utils.create_requests_proxy_dict()

    try:
        response_json = None
        # initialize the DataUtils
        data_utils = DataUtils(hostname=hostname, headers=headers, logger=None, proxy=proxies)

        url = const.ITERATOR_COMMON_URL.format(hostname=hostname, iterator_name=iterator_name)

        response = data_utils.make_api_call("POST", url, params=params)

        if response.status_code == 202:
            response_json = response.json()
            pattern = r'{}_[\w-]+'.format(re.escape(iterator_name))
            netskope_iterator_name = re.search(pattern, response_json.get("message", "")).group()
            return message, _types, netskope_iterator_name
        elif response.status_code == 401:
            message = "Invalid creds. Please recheck Netskope credentials or Proxy settings."
        elif response.status_code == 403:
            message = "Token V2 has insufficient dataexport endpoint permissions."
        else:
            message = "Received status code: {} and response: {}".format(response.status_code, response.text)

    except (requests.exceptions.ProxyError, socks.ProxyError) as ex:
        message = "Please recheck your Proxy settings. Error: {}".format(str(ex))
    except Exception as ex:
        message = "Error occured while validating Token V2 parameter. Error: {}".format(
            str(response_json.get("message") if response_json else ex)
        )

    return message, _types, netskope_iterator_name


def iterator_token_validator(hostname, token, endpoint_types, iterator_name):
    """Validate the v2 token for iterator inputs."""
    err_msgs = {}
    validation_msg = "success"
    netskope_iterator_name = None
    type_mapping = {
        "clientstatus": "ClientStatus",
        "page": "Connection",
        "application": "Application",
        "network": "Network"
    }
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(endpoint_types)) as executor:
        future_to_res = {
            executor.submit(
                make_rest_call_iterator,
                hostname,
                token,
                _types,
                iterator_name
            ): _types for _types in endpoint_types
        }
        for future in concurrent.futures.as_completed(future_to_res):
            try:
                message, _types, netskope_iterator_name = future.result()
                if message:
                    if message in err_msgs:
                        err_msgs.get(message).append(type_mapping.get(_types))
                    else:
                        err_msgs[message] = [type_mapping.get(_types)]
            except Exception:
                pass
    if len(err_msgs) > 0:
        validation_msg = ""
        for msg in err_msgs:
            validation_msg += "[" + " | ".join(err_msgs[msg]) + "] => " + msg + " "
        return False, validation_msg, None
    return True, validation_msg, netskope_iterator_name
