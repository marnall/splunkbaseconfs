#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test  # isort: skip # noqa F401

"""
This module will be used to get oauth token from auth code
"""

import json
import logging
import urllib.parse as urllib
import okta_utils as utils
from constant import DEFAULT_SCOPE
import sys
import re

import requests
import splunk.admin as admin

from solnlib import conf_manager, log
from solnlib.utils import is_true

logger = log.Logs().get_logger("splunk_ta_okta_identity_cloud_oauth")


class splunk_ta_okta_identity_cloud_rh_oauth2_token(admin.MConfigHandler):
    """
    REST Endpoint of getting token by OAuth2 in Splunk Add-on UI Framework.
    """

    def setup(self):
        """
        This method checks which action is getting called and what parameters are required for the request.
        """
        if self.requestedAction == admin.ACTION_EDIT:
            # Add required args in supported args
            for arg in ("url", "method", "grant_type", "client_id", "client_secret"):
                self.supportedArgs.addReqArg(arg)

            for arg in (
                "scope",  # Required for client_credentials
                "code",  # Required for authorization_code
                "redirect_uri",  # Required for authorization_code
            ):
                self.supportedArgs.addOptArg(arg)
        return

    def handleEdit(self, confInfo):
        """
        This handler is to get access token from the auth code received
        It takes 'url', 'method', 'grant_type', 'code', 'client_id', 'client_secret', 'redirect_uri', 'scope' as caller args and
        Returns the confInfo dict object in response.
        """
        try:
            logger.info("In OAuth rest handler to get access token")
            # Get args parameters from the request
            url = self.callerArgs.data["url"][0]
            grant_type = self.callerArgs.data["grant_type"][0]
            logger.info(f"OAuth url : {url}, Grant Type : {grant_type}")
            proxy_info = utils.get_proxy_settings(self.getSessionKey(), logger)

            method = self.callerArgs.data["method"][0]
            # Create payload from the arguments received
            scope = self.callerArgs.data.get("scope", [None])[0]
            payload = {
                "grant_type": self.callerArgs.data["grant_type"][0],
                "client_id": self.callerArgs.data["client_id"][0],
                "client_secret": self.callerArgs.data["client_secret"][0],
                "scope": scope.strip()
                if scope and scope.strip().lower() != "none"
                else DEFAULT_SCOPE,
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
            elif grant_type not in ("client_credentials",):
                # Only support two types ["authorization_code", "client_credentials"]
                logger.error("Invalid grant_type %s", grant_type)
                raise ValueError(
                    "Invalid grant_type %s. Supported values are authorization_code and client_credentials"
                    % grant_type
                )

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
            }
            # Send http request to get the access_token
            resp = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=urllib.urlencode(payload),
                proxies=proxy_info,
                timeout=90,
            )
            content = json.loads(resp.content)
            # Check for any errors in response. If no error then add the content values in confInfo
            if resp.status_code == 200:
                scope_granted = content["scope"]
                # Checking if there are no scopes assigned to the Okta Web App
                # If the condition is true, the error message willbe displayed in the UI
                # and process will be exited
                if scope_granted == "offline_access":
                    error_message = "No scopes are granted to the Okta Web App. Please provide appropriate scopes to the Okta Web App"
                    logger.error(error_message)
                    confInfo["token"]["error"] = error_message
                    return None
                for key, val in content.items():
                    confInfo["token"][key] = val
            else:
                # Else add the error message in the confinfo to display in the UI
                confInfo["token"]["error"] = (
                    content.get("error_description")
                    or content.get("errorSummary")
                    or "An unknown error occurred. Please check the logs for more details."
                )

            logger.info(
                f"Exiting OAuth rest handler after getting access token with response : {resp.status_code}"
            )
        except requests.exceptions.ConnectionError as ce:
            error_msg = str(ce)
            # Check for DNS resolution failure
            if (
                "Temporary failure in name resolution" in error_msg
                or "Name or service not known" in error_msg
            ):
                match = re.search(r"host='([^']+)'", error_msg)
                host = match.group(1) if match else "unknown"

                confInfo["token"]["error"] = (
                    f"Unable to resolve the domain '{host}'. "
                    "Please ensure the Okta domain is correct and reachable from the network."
                )
            else:
                confInfo["token"]["error"] = (
                    "A connection error occurred while contacting the Okta service. "
                    "Please verify your configuration details and network connectivity."
                )
            logger.error(f"Error occurred while fetching access token: {error_msg}")

        except Exception as exc:
            confInfo["token"]["error"] = (
                "An exception occurred while contacting the Okta service. "
                "Please verify your configuration details and network connectivity. "
                "Check the logs for more details."
            )
            logger.error(f"Error occurred while fetching access token: {str(exc)}")


if __name__ == "__main__":
    admin.init(
        splunk_ta_okta_identity_cloud_rh_oauth2_token, admin.CONTEXT_APP_AND_USER
    )
