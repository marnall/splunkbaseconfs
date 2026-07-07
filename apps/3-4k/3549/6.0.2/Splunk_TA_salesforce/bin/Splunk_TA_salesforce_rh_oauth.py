#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""
This module will be used to get oauth token from auth code

This file contains certain ignores for certain linters.

* isort ignores:
- isort: skip = Particular import must be the first import.

* flake8 ignores:
- noqa: F401 -> Def = module imported but unused
    Reason for ignoring = This is necessary as it contains adding a path to sys.path
"""

import import_declare_test  # isort: skip # noqa: F401
import json
from urllib.parse import urlencode

import requests
import sfdc_utility as su
import splunk.admin as admin


class splunk_ta_salesforce_rh_oauth2_token(admin.MConfigHandler):

    """
    This method checks which action is getting called and what parameters are required for the request.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.sfdc_util_ob = su.SFDCUtil(
            log_file="splunk_ta_salesforce_rh_oauth2_token",
            session_key=self.getSessionKey(),
        )

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
            self.sfdc_util_ob.logger.debug("In OAuth rest handler to get access token")
            # Get args parameters from the request
            url = self.callerArgs.data["url"][0]
            self.sfdc_util_ob.logger.debug("OAuth url %s", url)
            proxy_info = self.sfdc_util_ob.build_proxy_info()

            method = self.callerArgs.data["method"][0]
            grant_type = self.callerArgs.data["grant_type"][0]
            payload = {
                "grant_type": grant_type,
                "client_id": self.callerArgs.data["client_id"][0],
                "client_secret": self.callerArgs.data["client_secret"][0],
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
                self.sfdc_util_ob.logger.error("Invalid grant_type %s" % grant_type)
                raise ValueError(
                    "Invalid grant_type %s. Supported values are authorization_code and client_credentials"
                    % grant_type
                )

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
            }
            # Send http request to get the access token
            sslconfig = self.sfdc_util_ob.get_sslconfig()
            resp = requests.request(
                method,
                url,
                headers=headers,
                proxies=proxy_info,
                timeout=120,
                data=urlencode(payload),
                verify=sslconfig,
            )
            content = resp.content
            content = json.loads(content)
            # Check for any errors in response. If no error then add the content values in confInfo
            if resp.status_code == 200:
                for key, val in content.items():
                    confInfo["token"][key] = val
            else:
                # Else add the error message in the confinfo
                confInfo["token"]["error"] = content["error_description"]
            self.sfdc_util_ob.logger.info(
                "Exiting OAuth rest handler after getting access token with response %s",
                resp.status_code,
            )
        except Exception as exc:
            self.sfdc_util_ob.logger.error(
                "Error occurred while getting access token using auth code"
            )
            raise exc


if __name__ == "__main__":
    admin.init(splunk_ta_salesforce_rh_oauth2_token, admin.CONTEXT_APP_AND_USER)
