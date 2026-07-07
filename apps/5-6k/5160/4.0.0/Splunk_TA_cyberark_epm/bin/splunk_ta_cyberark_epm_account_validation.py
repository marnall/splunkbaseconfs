#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""
This module validates account being saved by the user
"""

import ipaddress
import json
import re
import socket
import traceback

import requests

# isort: off
import import_declare_test  # noqa: F401
import splunk.admin as admin  # noqa: F401
from cyberark_epm_utils import (
    get_cyberark_epm_api_version,
    get_proxy_settings,
    get_account_details,
    add_ucc_error_logger,
)
from solnlib import log
from splunktaucclib.rest_handler.error import RestError
from splunktaucclib.rest_handler.endpoint.validator import Validator
from constants import (
    SERVER_ERROR,
    CONNECTION_ERROR,
    AUTHENTICATION_ERROR,
    PERMISSION_ERROR,
    CONFIGURATION_ERROR,
)

_LOGGER = log.Logs().get_logger("splunk_ta_cyberark_epm_account_validation")


class GetSessionKey(admin.MConfigHandler):
    def __init__(self):
        self.session_key = self.getSessionKey()


def account_validation(
    url,
    username,
    password,
    session_key,
    auth_type="basic",
    identity_url=None,
    app_alias=None,
):
    """
    This method verifies the credentials by making an API call.
    Supports both basic (username/password) and OAuth2 (client_credentials) authentication.
    """
    if auth_type == "oauth2":
        return _validate_oauth2(
            url, username, password, session_key, identity_url, app_alias
        )
    return _validate_basic(url, username, password, session_key)


def _validate_oauth2(
    url, client_id, client_secret, session_key, identity_url, app_alias
):
    """
    Validates OAuth2 credentials by requesting a token from CyberArk Identity.
    """
    _LOGGER.debug(
        "Verifying OAuth2 credentials for Identity tenant {}".format(identity_url)
    )
    if not identity_url or not client_id or not client_secret or not app_alias:
        raise RestError(
            400,
            "Provide all necessary arguments: Identity Tenant URL, Client ID, Client Secret, and App Alias.",
        )
    if not url:
        raise RestError(400, "Provide the EPM Server URL.")
    if not identity_url.startswith("https://"):
        raise RestError(400, "Identity Tenant URL must start with https.")

    # Validate identity_url does not resolve to private IP (SSRF protection)
    try:
        from urllib.parse import urlparse

        parsed_identity = urlparse(identity_url)
        if not parsed_identity.hostname:
            raise RestError(
                400, "Identity Tenant URL does not contain a valid hostname."
            )
        identity_ip = socket.gethostbyname(parsed_identity.hostname)
        if ipaddress.ip_address(identity_ip).is_private:
            raise RestError(
                400, "Identity Tenant URL must not resolve to a private IP address."
            )
    except socket.gaierror:
        raise RestError(
            400, "Identity Tenant URL could not be resolved. Check the hostname."
        )
    except (ValueError, ipaddress.AddressValueError):
        raise RestError(400, "Invalid IP address in Identity Tenant URL.")

    if not url.startswith("https://"):
        raise RestError(400, "EPM Server URL must start with https.")
    if not re.match(r"^[a-zA-Z0-9_\-]+$", app_alias):
        raise RestError(
            400,
            "App Alias must contain only alphanumeric characters, underscores, and hyphens.",
        )

    token_url = "{}/oauth2/token/{}".format(identity_url.rstrip("/"), app_alias)
    try:
        proxy_settings = get_proxy_settings(_LOGGER, session_key)
        resp = requests.post(
            url=token_url,
            proxies=proxy_settings,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Splunk-TA-CyberArkEPM/1.0",
            },
            timeout=120,
            allow_redirects=False,
        )
    except Exception as e:
        msg = (
            "Could not connect to {}. Check configuration and network settings.".format(
                token_url
            )
        )
        add_ucc_error_logger(_LOGGER, CONNECTION_ERROR, e, msg_before=msg)
        raise RestError(400, msg)

    if resp.status_code == 200:
        try:
            resp_data = resp.json()
            if resp_data.get("access_token"):
                access_token = resp_data["access_token"]
                sets_url = "{}/EPM/API/{}/Sets".format(
                    url.rstrip("/"), get_cyberark_epm_api_version()
                )
                try:
                    epm_resp = requests.get(
                        url=sets_url,
                        proxies=proxy_settings,
                        headers={
                            "Authorization": "Bearer " + access_token,
                            "Content-Type": "application/json",
                            "User-Agent": "Splunk-TA-CyberArkEPM/1.0",
                        },
                        timeout=120,
                        allow_redirects=False,
                    )
                except Exception as e:
                    msg = "OAuth2 token obtained, but could not connect to EPM server {}. Check the EPM Server URL.".format(
                        url
                    )
                    add_ucc_error_logger(_LOGGER, CONNECTION_ERROR, e, msg_before=msg)
                    raise RestError(400, msg)
                if epm_resp.status_code == 200:
                    _LOGGER.info(
                        "OAuth2 credentials and EPM Server URL successfully validated."
                    )
                    return True
                if epm_resp.status_code == 401:
                    e = Exception("ERROR [401] - EPM server rejected the OAuth2 token.")
                    add_ucc_error_logger(_LOGGER, AUTHENTICATION_ERROR, e)
                    raise RestError(
                        401,
                        "EPM Server rejected the OAuth2 token. Verify the EPM Server URL matches your Identity tenant configuration.",
                    )
                if epm_resp.status_code == 403:
                    e = Exception(
                        "ERROR [403] - EPM server access forbidden for this OAuth2 token."
                    )
                    add_ucc_error_logger(_LOGGER, PERMISSION_ERROR, e)
                    raise RestError(
                        403,
                        "Access to EPM Server is forbidden for this token. Check account permissions.",
                    )
                e = Exception(
                    "ERROR [{}] - Unexpected EPM Server response.".format(
                        epm_resp.status_code
                    )
                )
                add_ucc_error_logger(_LOGGER, SERVER_ERROR, e)
                raise RestError(
                    epm_resp.status_code,
                    "EPM Server returned unexpected status {}. Check the EPM Server URL.".format(
                        epm_resp.status_code
                    ),
                )
            msg = "OAuth2 token response did not contain an access_token."
            _LOGGER.error(msg)
            raise RestError(400, msg)
        except RestError:
            raise
        except Exception as e:
            msg = "Unable to validate OAuth2 credentials, unexpected token response."
            _LOGGER.error("Exception raised: {}. {}".format(str(e), msg))
            raise RestError(400, msg)

    if resp.status_code == 400:
        try:
            error_detail = resp.json().get("error_description", "Invalid request")
        except Exception:
            error_detail = "Invalid request"
        e = Exception(
            "ERROR [{}] - OAuth2 token request failed.".format(resp.status_code)
        )
        add_ucc_error_logger(_LOGGER, AUTHENTICATION_ERROR, e)
        raise RestError(
            resp.status_code, "OAuth2 token request failed: {}".format(error_detail)
        )
    if resp.status_code == 401:
        e = Exception(
            "ERROR [{}] - Invalid OAuth2 credentials.".format(resp.status_code)
        )
        add_ucc_error_logger(_LOGGER, AUTHENTICATION_ERROR, e)
        raise RestError(
            resp.status_code, "Invalid OAuth2 credentials (Client ID or Client Secret)."
        )

    _LOGGER.error("OAuth2 error [{}].".format(resp.status_code))
    raise RestError(
        resp.status_code,
        "OAuth2 error {}. Could not obtain token from {}".format(
            resp.status_code, token_url
        ),
    )


def _validate_basic(url, username, password, session_key):
    """
    Validates basic (username/password) credentials against the EPM server.
    """

    _LOGGER.debug("Verifying username and password for the EPM instance {}".format(url))
    if not url or not username or not password:
        raise RestError(
            400, "Provide all necessary arguments : url , username and password."
        )

    if "https://" not in url:
        raise RestError(400, "Provided base URL of Cyberark EPM must start with https.")
    try:
        proxy_settings = get_proxy_settings(_LOGGER, session_key)

        headers = {
            "Content-type": "application/json",
            "Accept": "text/plain",
            "User-Agent": "Splunk-TA-CyberArkEPM/1.0",
        }
        body = {"Username": username, "Password": password, "ApplicationID": "Splunk"}
        api_url = url + "/EPM/API/{}/Auth/EPM/Logon".format(
            get_cyberark_epm_api_version()
        )

        resp = requests.post(
            url=api_url,
            proxies=proxy_settings,
            data=json.dumps(body),
            headers=headers,
            timeout=120,
        )

    except Exception as e:
        msg = (
            "Could not connect to {}. Check configuration and network settings".format(
                url
            )
        )
        add_ucc_error_logger(_LOGGER, CONNECTION_ERROR, e, msg_before=msg)

        raise RestError(400, msg)

    if resp.status_code in (200, 201):
        try:
            resp_data = resp.json()

            # Check if password has expired (API returns 200 but with IsPasswordExpired flag)
            if resp_data.get("IsPasswordExpired", False):
                msg = "Password has expired. Please reset your password before configuring this account."
                _LOGGER.error(f"Account validation failed: {msg}")
                raise RestError(403, msg)

            resp_data["EPMAuthenticationResult"]
            _LOGGER.info("Account credentials successfully validated.")
            return True
        except RestError:
            raise  # Re-raise RestError from password expired check
        except Exception as e:
            msg = (
                "Unable to validate the Account credentials, please check the details."
            )
            _LOGGER.error(f"Exception raised: {str(e)}. {msg}")
            raise RestError(resp.status_code, msg)

    if resp.status_code == 400:
        e = Exception(
            "ERROR [{}] - EPM server {} cannot or will not process the request due to Bad Request. {}".format(
                resp.status_code, url, resp.text
            )
        )
        add_ucc_error_logger(_LOGGER, CONNECTION_ERROR, e)
        raise RestError(
            resp.status_code, "EPM server cannot process the request. Bad Request."
        )
    if resp.status_code == 401:
        e = Exception(
            "ERROR [{}] - The request has not been applied because of Invalid Credentials. {}".format(
                resp.status_code, resp.text
            )
        )
        add_ucc_error_logger(_LOGGER, AUTHENTICATION_ERROR, e)
        raise RestError(resp.status_code, "Invalid Credentials.")
    if resp.status_code == 403:
        e = Exception(
            "ERROR [{}] - Access to the EPM server {} is forbidden for this user. {}".format(
                resp.status_code, url, resp.text
            )
        )
        add_ucc_error_logger(_LOGGER, PERMISSION_ERROR, e)
        raise RestError(
            resp.status_code, "Access to the EPM server is forbidden for this user."
        )
    if resp.status_code == 404:
        e = Exception(
            "ERROR [{}] - EPM server {} not found OR Invalid EPM url. {}".format(
                resp.status_code, url, resp.text
            )
        )
        add_ucc_error_logger(_LOGGER, CONNECTION_ERROR, e)
        raise RestError(resp.status_code, "EPM server not found OR Invalid EPM url.")
    if resp.status_code == 500:
        e = Exception(
            "ERROR [{}] - Internal Server Error. {}".format(resp.status_code, resp.text)
        )
        add_ucc_error_logger(_LOGGER, SERVER_ERROR, e)
        raise RestError(resp.status_code, "Internal Server Error.")

    _LOGGER.error("Error [{}]. {}".format(resp.status_code, resp.text))
    raise RestError(
        resp.status_code,
        "ERROR {}. Could not connect to {}".format(resp.status_code, url),
    )


class AccountNameValidation(Validator):
    """
    Account name validation
    """

    def __init__(self, *args, **kwargs):
        super(AccountNameValidation, self).__init__(*args, **kwargs)

    def validate(self, value, data):
        """
        This function validates the account_name present in the payload when saving an input
        It validates that any account with provided account_name is configured or not.
        """
        try:
            session_key = GetSessionKey().session_key
            account_details = get_account_details(_LOGGER, session_key, value)
            auth_type = account_details.get("auth_type", "basic")
            if auth_type == "oauth2":
                required_fields = [
                    "client_id",
                    "client_secret",
                    "epm_url",
                    "identity_url",
                    "app_alias",
                ]
            else:
                required_fields = ["username", "password", "epm_url"]
            if all(account_details.get(f) for f in required_fields):
                return True
            errorMsg = "Configurations missing for account with name: {}.".format(value)
            self.put_msg(errorMsg)
            return False
        except Exception:
            errorMsg = "No account found with name: {}.".format(value)
            e = Exception(errorMsg)
            add_ucc_error_logger(_LOGGER, CONFIGURATION_ERROR, e)
            self.put_msg(errorMsg)
            return False
