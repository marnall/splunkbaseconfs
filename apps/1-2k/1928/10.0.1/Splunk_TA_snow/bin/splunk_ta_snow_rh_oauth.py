#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#


import re
import import_declare_test  # isort: skip # noqa: F401
import sys

import requests

"""
This module is used to get oauth token from auth code
"""

import json
import os.path as op
import urllib.parse as urllib

import splunk.admin as admin
from snow_utility import (
    get_sslconfig,
    contains_js_tags,
    create_log_object,
    build_proxy_info,
)
from snow_consts import APP_NAME
from solnlib import conf_manager, log
from solnlib.utils import is_true


log.Logs.set_context()
logger = create_log_object("splunk_ta_snow_main")


"""
REST Endpoint of getting token by OAuth2 in Splunk Add-on UI Framework.
"""


class splunk_ta_snow_rh_oauth2_token(admin.MConfigHandler):

    """
    This method checks which action is getting called and what parameters are required for the request.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        session_key = self.getSessionKey()
        log_level = conf_manager.get_log_level(
            logger=logger,
            session_key=session_key,
            app_name=APP_NAME,
            conf_name="splunk_ta_snow_settings",
            log_stanza="logging",
            log_level_field="loglevel",
        )
        log.Logs().set_level(log_level)

    def setup(self):
        """
        Checks which action is getting called and what parameters are required for the request.
        """
        if self.requestedAction == admin.ACTION_EDIT:

            # Add required args in supported args
            for arg in ("url", "method", "grant_type", "client_id", "client_secret"):
                self.supportedArgs.addReqArg(arg)

            for arg in (
                "scope",  # Optional for client_credentials
                "code",  # Required for authorization_code
                "redirect_uri",  # Required for authorization_code
            ):
                self.supportedArgs.addOptArg(arg)
        return

    """
    This handler is to get access token from the auth code received
    It takes 'url', 'method', 'grant_type', 'code', 'client_id', 'client_secret', 'redirect_uri' as caller args and
    Returns the confInfo dict object in response.
    """

    def handleEdit(self, confInfo):

        try:
            logger.debug("In OAuth rest handler to get access token")
            # Get args parameters from the request
            url = self.callerArgs.data["url"][0]
            logger.debug("oAUth url %s", url)
            proxy_info = self.getProxyDetails()
            method, grant_type, client_id, client_secret = (
                self.callerArgs.data["method"][0],
                self.callerArgs.data["grant_type"][0],
                self.callerArgs.data["client_id"][0],
                self.callerArgs.data["client_secret"][0],
            )
            for key in [method, grant_type, client_id, client_secret]:
                if contains_js_tags(key):
                    logger.error(
                        "Exiting OAuth rest handler: {} contains scripting tags".format(
                            key
                        )
                    )
                    raise ValueError("{} contains scripting tags".format(key))

            # Create payload from the arguments received
            payload = {
                "grant_type": grant_type,
                "client_id": client_id,
                "client_secret": client_secret,
            }

            if grant_type == "authorization_code":
                # If grant_type is authorization_code then add code and redirect_uri in payload
                for param_name in ("code", "redirect_uri"):
                    param = self.callerArgs.data.get(param_name, [None])[0]

                    if param is None:
                        raise ValueError(
                            "%s is required for authorization_code grant type"
                            % param_name
                        )

                    payload[param_name] = param
            elif grant_type == "client_credentials":
                # If grant_type is client_credentials add scope exists then add it in payload
                scope = self.callerArgs.data.get("scope", [None])[0]

                if scope:
                    payload["scope"] = scope
            else:
                # Else raise an error
                logger.error("Invalid grant_type %s" % grant_type)
                raise ValueError(
                    "Invalid grant_type %s. Supported values are authorization_code and client_credentials"
                    % grant_type
                )

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
            }
            session_key = self.getSessionKey()
            sslconfig = get_sslconfig({}, session_key, logger)
            # Send http request to get the accesstoken
            # semgrep ignore reason: we have custom handling for unsuccessful HTTP status codes
            resp = requests.request(  # nosemgrep: python.requests.best-practice.use-raise-for-status.use-raise-for-status  # noqa: E501
                method,
                url,
                headers=headers,
                data=urllib.urlencode(payload),
                proxies=proxy_info,
                timeout=120,
                verify=sslconfig,
            )
            content = json.loads(resp.content)
            # Check for any errors in response. If no error then add the content values in confInfo
            if resp.status_code == 200:
                for key, val in content.items():  # py2/3
                    confInfo["token"][key] = val
                logger.info(  # nosemgrep: python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure  # noqa: E501
                    "Exiting OAuth rest handler after getting access token with response {}".format(
                        resp.status_code
                    )
                )
            else:
                # Else add the error message in the confinfo and logs
                confInfo["token"]["error"] = content["error_description"]
                logger.error(
                    "Exiting OAuth rest handler with status code {}. Server responded with {}".format(
                        resp.status_code,
                        str(confInfo["token"]["error"]),
                    )
                )
        except Exception as exc:
            # Fixed `python.lang.best-practice.logging-error-without-handling.logging-error-without-handling`
            logger.warning("Error occurred while getting access token using auth code")
            raise exc

    def getProxyDetails(self):
        """
        Get proxy details stored in settings conf file
        """
        # Create confmanger object for the app with realm
        cfm = conf_manager.ConfManager(
            self.getSessionKey(),
            "Splunk_TA_snow",
            realm="__REST_CREDENTIAL__#Splunk_TA_snow#configs/conf-splunk_ta_snow_settings",
        )
        # Get Conf object of apps settings
        conf = cfm.get_conf("splunk_ta_snow_settings")
        # Get proxy stanza from the settings
        proxy_config = conf.get("proxy", True)
        return build_proxy_info(proxy_config)

    def is_valid_port(self, port):
        """
        Method to check if the given port is valid or not
        :param port: port number to be validated
        :type port: ``int``
        """
        try:
            return 0 < int(port) <= 65535
        except ValueError:
            return False


if __name__ == "__main__":
    admin.init(splunk_ta_snow_rh_oauth2_token, admin.CONTEXT_APP_AND_USER)
