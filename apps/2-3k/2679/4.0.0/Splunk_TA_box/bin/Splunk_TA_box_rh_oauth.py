#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
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

import requests
import splunk.admin as admin
from box_utility import get_sslconfig
from framework import log_files
from solnlib import conf_manager, log
from solnlib.utils import is_true
from box_helper import get_proxy_logging_config

logger = log.Logs().get_logger(log_files.ta_box_rh_oauth)


class splunk_ta_box_rh_oauth2_token(admin.MConfigHandler):
    """
    REST Endpoint of getting token by OAuth2 in Splunk Add-on UI Framework.
    """

    def __init__(self, *args, **kwargs):
        admin.MConfigHandler.__init__(self, *args, **kwargs)
        _, logging_config = get_proxy_logging_config(self.getSessionKey())
        logger.setLevel(logging_config.get("loglevel", "INFO"))

    def setup(self):
        """
        This method checks which action is getting called and what parameters are required for the request.
        """
        if self.requestedAction == admin.ACTION_EDIT:
            # Add required args in supported args
            for arg in ("url", "method", "grant_type", "client_id", "client_secret"):
                self.supportedArgs.addReqArg(arg)

            for arg in (
                "scope",  # Optional for client_credentials
                "code",  # Required for authorization_code
                "redirect_uri",  # Required for authorization_code
                "box_subject_id",  # Required for client_credentials
                "box_subject_type",  # Required for client_credentials
            ):
                self.supportedArgs.addOptArg(arg)
        return

    def handleEdit(self, confInfo):
        """
        This handler is to get access token from the auth code received
        It takes 'url', 'method', 'grant_type', 'code', 'client_id', 'client_secret', 'redirect_uri' as caller args and
        Returns the confInfo dict object in response.
        """
        try:
            logger.debug("In OAuth rest handler to get access token")
            # Get args parameters from the request
            url = self.callerArgs.data["url"][0]
            logger.debug("oAUth url %s", url)
            proxy_info = self.getProxyDetails()
            disable_ssl_validation = self.getSSLDetails()
            method = self.callerArgs.data["method"][0]
            # Create payload from the arguments received
            grant_type = self.callerArgs.data["grant_type"][0]

            payload = {
                "grant_type": self.callerArgs.data["grant_type"][0],
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

                param = self.callerArgs.data.get("box_subject_id", [None])[0]
                if param is None:
                    raise ValueError(
                        "box_subject_id is required for client_credentials grant type"
                    )

                payload["box_subject_id"] = param
                payload["box_subject_type"] = "user"
            else:
                # Else raise an error
                logger.error("Invalid grant_type %s", grant_type)
                raise ValueError(
                    "Invalid grant_type %s. Supported values are authorization_code and client_credentials"
                    % grant_type
                )

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
            }
            # Send http request to get the accesstoken
            session_key = self.getSessionKey()
            sslconfig = get_sslconfig(session_key, disable_ssl_validation)
            resp = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=urllib.urlencode(payload),
                proxies=proxy_info,
                timeout=import_declare_test.DEFAULT_API_REQUESTS_TIMEOUT,
                verify=sslconfig,
            )
            content = json.loads(resp.content)
            # Check for any errors in response. If no error then add the content values in confInfo
            if resp.status_code == 200:
                for key, val in content.items():
                    confInfo["token"][key] = val
            else:
                # Else add the error message in the confinfo
                confInfo["token"]["error"] = content["error_description"]
            logger.info(
                "Exiting OAuth rest handler after getting access token with response %s",
                resp.status_code,
            )
        except Exception as exc:
            logger.exception(
                "Error occurred while getting access_token using auth code"
            )
            raise

    def getProxyDetails(self):
        """
        This method is to get proxy details stored in settings conf file
        """
        # Create confmanger object for the app with realm
        cfm = conf_manager.ConfManager(
            self.getSessionKey(),
            "Splunk_TA_box",
            realm="__REST_CREDENTIAL__#Splunk_TA_box#configs/conf-splunk_ta_box_settings",
        )
        # Get Conf object of apps settings
        conf = cfm.get_conf("splunk_ta_box_settings")
        # Get proxy stanza from the settings
        proxy_config = conf.get("proxy", True)
        if not proxy_config or not is_true(proxy_config.get("proxy_enabled")):
            logger.info("Proxy is not enabled")
            return None

        url = proxy_config.get("proxy_url")
        port = proxy_config.get("proxy_port")

        if url or port:
            if not url:
                raise ValueError('Proxy "url" must not be empty')
            if not self.is_valid_port(port):
                raise ValueError('Proxy "port" must be in range [1,65535]: %s' % port)

        user = proxy_config.get("proxy_username")
        password = proxy_config.get("proxy_password")

        if not all((user, password)):
            logger.info("Proxy has no credentials found")
            user, password = None, None

        proxy_type = (proxy_config.get("proxy_type") or "http").lower()
        if proxy_type not in ("http", "socks5"):
            logger.info('Proxy type not found, set to "HTTP"')
            proxy_type = "http"

        rdns = is_true(proxy_config.get("proxy_rdns"))
        # socks5 causes the DNS resolution to happen on the client
        # socks5h causes the DNS resolution to happen on the proxy server
        if rdns and proxy_type == "socks5":
            proxy_type = "socks5h"

        if user and password:
            encoded_user = urllib.quote(user)
            encoded_password = urllib.quote(password)
            proxy_info = {
                "http": f"{proxy_type}://{encoded_user}:{encoded_password}@{url}:{port}"
            }
        else:
            proxy_info = {"http": f"{proxy_type}://{url}:{port}"}

        proxy_info["https"] = proxy_info["http"]

        return proxy_info

    def getSSLDetails(self):
        """
        Method to fetch value of disable_ssl_certificate_validation parameter
        :param port: port number to be validated
        :type disable_ssl_validation: ``bool``
        """
        box_cfm = conf_manager.ConfManager(
            self.getSessionKey(),
            "Splunk_TA_box",
            realm="__REST_CREDENTIAL__#Splunk_TA_box#configs/conf-box",
        )

        box_conf = box_cfm.get_conf("box").get_all()

        disable_ssl_validation = box_conf["box_default"].get(
            "disable_ssl_certificate_validation"
        )
        return is_true(disable_ssl_validation)

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
    admin.init(splunk_ta_box_rh_oauth2_token, admin.CONTEXT_APP_AND_USER)
