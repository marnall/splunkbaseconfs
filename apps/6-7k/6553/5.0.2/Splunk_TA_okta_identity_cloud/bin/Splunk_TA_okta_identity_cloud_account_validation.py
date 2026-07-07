##
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

import sys

import okta_utils as utils
import requests
import splunk.admin as admin
from solnlib import log
from splunktaucclib.rest_handler.endpoint.validator import Validator


class GetSessionKey(admin.MConfigHandler):
    def __init__(self):
        self.session_key = self.getSessionKey()


class AccountValidation(Validator):
    """
    Account/Server Validation
    """

    def __init__(self, *args, **kwargs):
        super(AccountValidation, self).__init__(*args, **kwargs)

    def validate(self, value, data):
        """
        This function validates if the entered domain and api token are valid or not.

        """
        log_filename = "splunk_ta_okta_identity_cloud_account_validation"
        logger = log.Logs().get_logger(log_filename)

        logger.debug("Getting session key")
        session_key = GetSessionKey().session_key

        domain = data.get("domain")
        password = data.get("password")

        url = "https://{}/api/v1/users".format(domain)
        logger.debug("Getting proxy settings")
        proxy = utils.get_proxy_settings(session_key, logger)

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "SSWS {}".format(password),
        }
        try:
            response = requests.request(
                "GET", url, headers=headers, proxies=proxy, timeout=90
            )
        except Exception as e:
            logger.error(
                "Exception occurred while validating the account. Message - {}".format(
                    e
                )
            )
            errorMsg = "Make sure your Okta Domain and API Token is valid"
            self.put_msg(errorMsg)
            return False
        if response.status_code not in (200, 201):
            logger.info(
                "Invalid account credentials provided. Please verify the credentials. Error [{}] : {}".format(
                    response.status_code, response.text
                )
            )
            try:
                errorMsg = response.json().get("errorSummary")
            except Exception as e:
                errorMsg = "Unknown error: Please verify that the domain and credentials provided are correct."
            self.put_msg(errorMsg)
            return False
        else:
            logger.info("Account credentials successfully validated.")
            return True
