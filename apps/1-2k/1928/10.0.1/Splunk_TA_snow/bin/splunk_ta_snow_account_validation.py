#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import base64
import copy
import json
import re
import traceback

import requests
import splunk.admin as admin
from snow import proxy_port_value_validation
import snow_consts
from snow_utility import (
    get_sslconfig,
    contains_js_tags,
    build_proxy_info,
    add_ucc_error_logger,
    create_log_object,
)
from solnlib import conf_manager, log, utils
from splunktaucclib.rest_handler.endpoint.validator import Validator


APP_NAME = "Splunk_TA_snow"
_LOGGER = create_log_object("splunk_ta_snow_main")


class GetSessionKey(admin.MConfigHandler):
    def __init__(self):
        self.session_key = self.getSessionKey()


class EndpointValidation(Validator):
    """
    Validate Endpoint URL
    """

    def __init__(self, *args, **kwargs):
        super(EndpointValidation, self).__init__(*args, **kwargs)

    def validate(self, value, data):

        _LOGGER.debug("Verifying endpoint for ServiceNow instance {}.".format(value))

        url_pattern = r"^[a-zA-Z0-9\\.\-:\/]+"
        if re.match(url_pattern, value):
            _LOGGER.debug(
                "Provided endpoint URL for ServiceNow instance {} is valid.".format(
                    value
                )
            )
            return True

        else:
            msg = "Invalid URL {} provided.".format(value)
            _LOGGER.error(msg)

            self.put_msg(msg)
            return False


class TokenValidation(Validator):
    """
    Validate given access_token
    """

    def __init__(self, *args, **kwargs):
        super(TokenValidation, self).__init__(*args, **kwargs)

    def validate(self, value, data):

        if contains_js_tags(value):
            msg = "Invalid access_token provided."
            _LOGGER.error(msg)
            self.put_msg(msg)
            return False
        else:
            return True


class RefreshTokenValidation(Validator):
    """
    Validate given refresh_token
    """

    def __init__(self, *args, **kwargs):
        super(RefreshTokenValidation, self).__init__(*args, **kwargs)

    def validate(self, value, data):

        if contains_js_tags(value):
            msg = "Invalid refresh_token provided."
            _LOGGER.error(msg)
            self.put_msg(msg)
            return False
        else:
            return True


class ClientIDValidation(Validator):
    """
    Validate given client_id
    """

    def __init__(self, *args, **kwargs):
        super(ClientIDValidation, self).__init__(*args, **kwargs)

    def validate(self, value, data):

        _LOGGER.debug("Verifying client_id {}.".format(value))

        if contains_js_tags(value):
            msg = "Invalid client_id {} provided.".format(value)  # noqa : E501
            _LOGGER.error("Invalid client_id {} provided.".format(value))
            self.put_msg(msg)
            return False
        else:
            _LOGGER.info("Provided client_id {} is valid.".format(value))
            return True


class URLValidation(Validator):
    """
    Validate ServiceNow URL
    """

    def __init__(self, *args, **kwargs):
        super(URLValidation, self).__init__(*args, **kwargs)

    def validate(self, value, data):

        url = data["url"]
        _LOGGER.debug("Verifying URL for ServiceNow instance {}.".format(url))

        url_pattern = r"^(https:\/\/)[^\/]+\/?$"
        if re.match(url_pattern, url):
            _LOGGER.debug(
                "Entered URL for ServiceNow instance {} is valid.".format(url)
            )
            return True

        else:
            msg = "Invalid URL {} provided. Please provide URL in this format: https://myaccount.service-now.com".format(  # noqa : E501
                url
            )
            _LOGGER.error(msg)
            self.put_msg(msg)
            return False


class AccountValidation(Validator):
    """
    Validate ServiceNow account details
    """

    def __init__(self, *args, **kwargs):
        super(AccountValidation, self).__init__(*args, **kwargs)

    def getProxySettings(self, defaults):
        # Obtain proxy settings, if proxy has been configured, by reading splunk_ta_snow_settings.conf
        session_key_obj = GetSessionKey()
        session_key = session_key_obj.session_key

        settings_cfm = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm="__REST_CREDENTIAL__#{}#configs/conf-splunk_ta_snow_settings".format(
                APP_NAME
            ),
        )

        splunk_ta_snow_settings_conf = settings_cfm.get_conf(
            "splunk_ta_snow_settings"
        ).get_all()

        for key, value in splunk_ta_snow_settings_conf["proxy"].items():
            defaults[key] = value

        return defaults

    def validate(self, value, data):
        _LOGGER.info(
            "Verifying username and password for ServiceNow instance {}.".format(
                data["url"]
            )
        )
        defaults = self.getProxySettings(copy.deepcopy(data))
        if (
            utils.is_true(defaults.get("proxy_enabled") or "0")
            and "proxy_port" in defaults
            and not proxy_port_value_validation(defaults["proxy_port"])
        ):
            self.put_msg(
                "Invalid Proxy Port value in Configuration file,Proxy Port "
                "should be within the range of [1 and 65535]"
            )
            return False

        url = defaults["url"]

        data = empty_values(data)
        if not data:
            return False
        if data.get("auth_type", "") in ["oauth", "oauth_client_credentials"]:
            # exiting for oauth auth_type as its account validation is already done in JS.
            return True

        # Validate username and password for the account url entered
        uri = (
            "{}/incident.do?JSONv2&sysparm_query="
            "sys_updated_on>=2000-01-01+00:00:00&sysparm_record_count=1"
        )
        url = uri.format(url)
        proxy_info = build_proxy_info(defaults)
        session_key = GetSessionKey().session_key
        sslconfig = get_sslconfig(defaults, session_key, _LOGGER)
        try:
            credentials = base64.urlsafe_b64encode(
                ("%s:%s" % (defaults["username"], defaults["password"])).encode("UTF-8")
            ).decode("ascii")
            headers = {"Authorization": "Basic %s" % credentials}
            # semgrep ignore reason: we have custom handling for unsuccessful HTTP status codes
            resp = requests.request(  # nosemgrep: python.requests.best-practice.use-raise-for-status.use-raise-for-status  # noqa: E501
                "GET",
                url,
                headers=headers,
                proxies=proxy_info,
                timeout=120,
                verify=sslconfig,
            )
            content = resp.content
        except requests.exceptions.ProxyError as e:
            msg = "Unable to connect to Proxy. For more details, please check the splunk_ta_snow_main.log file."
            error_msg = "Unable to connect to Proxy. Error occured: {}".format(e)
            add_ucc_error_logger(
                logger=_LOGGER,
                logger_type=snow_consts.CONNECTION_ERROR,
                exception=e,
                msg_before=error_msg,
            )
            self.put_msg(msg)
            return False
        except Exception as e:
            msg = "Unable to reach server at {}. Check configurations and network settings.".format(
                defaults["url"]
            )
            error_msg = "Unable to reach ServiceNow instance at {0}. The reason for failure is={1}".format(
                defaults["url"], traceback.format_exc()
            )
            add_ucc_error_logger(
                logger=_LOGGER,
                logger_type=snow_consts.CONNECTION_ERROR,
                exception=e,
                msg_before=error_msg,
            )

            self.put_msg(msg)
            return False
        else:
            if resp.status_code not in (200, 201):
                msg = (
                    "Failed to verify ServiceNow username and password, " "code={} ({})"
                ).format(resp.status_code, resp.reason)
                _LOGGER.error(
                    "Failure occurred while verifying username and password. Response code={} ({})".format(
                        resp.status_code, resp.reason
                    )
                )

                self.put_msg(msg)
                return False
            else:
                # This code is developed under ADDON-21364
                try:
                    json.loads(content)
                except ValueError as e:
                    msg = "Authentication failed. ServiceNow instance is suspended or inactive."
                    error_msg = "Error Message: {} \nContent : {}".format(msg, content)
                    add_ucc_error_logger(
                        logger=_LOGGER,
                        logger_type=snow_consts.CONNECTION_ERROR,
                        exception=e,
                        msg_before=error_msg,
                    )
                    self.put_msg(msg)
                    return False
                return True


class ProxyURLValidation(Validator):
    """
    Validate Proxy ServiceNow URL
    """

    def __init__(self, *args, **kwargs):
        super(ProxyURLValidation, self).__init__(*args, **kwargs)

    def validate(self, value, data):

        _LOGGER.debug("Verifying Proxy URL {}.".format(value))

        proxy_url_pattern = (
            r"^[a-zA-Z0-9:][a-zA-Z0-9\.\-\:]+(?:\/([a-zA-Z0-9\-\.\~\/]*))?$"
        )
        if re.match(proxy_url_pattern, value) and (0 < len(value) < 4096):
            _LOGGER.debug("Provided Proxy URL {} is valid.".format(value))
            return True

        else:
            msg = "Invalid Proxy URL {} provided.".format(value)
            _LOGGER.error(msg)
            self.put_msg(msg)
            return False


class ProxyValidation(Validator):
    """
    Validate Proxy details provided
    """

    def __init__(self, *args, **kwargs):
        super(ProxyValidation, self).__init__(*args, **kwargs)

    def validate(self, value, data):
        _LOGGER.info("Verifying proxy details")

        username_val = data.get("proxy_username")
        password_val = data.get("proxy_password")

        # If password is specified, then username is required
        if password_val and not username_val:
            self.put_msg("Username is required if password is specified")
            return False
        # If username is specified, then password is required
        elif username_val and not password_val:
            self.put_msg("Password is required if username is specified")
            return False

        # If length of username is not satisfying the String length criteria
        if username_val:
            str_len = len(username_val)
            _min_len = 1
            _max_len = 50
            if str_len < _min_len or str_len > _max_len:
                msg = (
                    "String length of username should be between %(min_len)s and %(max_len)s"
                    % {"min_len": _min_len, "max_len": _max_len}
                )
                self.put_msg(msg)
                return False

        return True


class RemoveRedundantParam(Validator):
    """
    Validates and removes redundant parameter based on account type selected
    """

    def __init__(self, *args, **kwargs):
        super(RemoveRedundantParam, self).__init__(*args, **kwargs)

    def validate(self, value, data):
        data = empty_values(data)
        return False if not data else True


class ProxyTypeValidation(Validator):
    """
    Validates on proxy_type
    """

    def __init__(self, *args, **kwargs):
        super(ProxyTypeValidation, self).__init__(*args, **kwargs)

    def validate(self, value, data):
        if data.get("proxy_type") == "http" or data.get("proxy_type") == "socks5":
            return True

        return False


class LogLevelValidation(Validator):
    """
    Validates on loglevel
    """

    def __init__(self, *args, **kwargs):
        super(LogLevelValidation, self).__init__(*args, **kwargs)

    def validate(self, value, data):
        if value in ["INFO", "DEBUG", "WARN", "ERROR", "CRITICAL"]:
            return True

        return False


def empty_values(data_dict):
    """
    Empties the values of keys irrelevant to auth_type selected. Logs an error
    of auth_type provided is invalid.
    """
    if data_dict.get("auth_type", "") == "basic":
        data_dict["endpoint"] = data_dict["refresh_token"] = data_dict[
            "access_token"
        ] = data_dict["client_id"] = data_dict["client_secret"] = ""
    elif data_dict.get("auth_type", "") == "oauth":
        data_dict["password"] = data_dict["username"] = ""
    elif data_dict.get("auth_type", "") == "oauth_client_credentials":
        data_dict["password"] = data_dict["username"] = data_dict["refresh_token"] = ""
    else:
        _LOGGER.error(
            "Received an invalid Authentication Type: {}. "
            "Please reconfigure the account.".format(
                data_dict.get("auth_type", "<no authentication type found>")
            )
        )
        return False

    return data_dict
