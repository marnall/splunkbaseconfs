#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
import logging
from defusedxml.ElementTree import fromstring as defused_fromstring
import requests
from logging_helper import get_logger
from splunktaucclib.rest_handler.endpoint.validator import Validator
import splunk_ta_cisco_ucs_constants as constants
import ciso_ucs_utils as utils
import ssl
import traceback
from solnlib import log

_LOGGER = get_logger(constants.TA_NAME.lower() + "_validation")


class AccountValidation(Validator):
    def __init__(self, *args, **kwargs):
        super(AccountValidation, self).__init__(*args, **kwargs)

    def validate(self, value, data):
        url = "https://{}/nuova".format(data["server_url"])
        headers = {"content-type": "application/xml"}
        payload = "<aaaLogin inName='{}' inPassword='{}'></aaaLogin>".format(
            data["account_name"], data["account_password"]
        )
        resp, content = None, None

        try:
            # Note: to update server after disabling ssl certification verification
            # from backend, user will need to update it from backend only
            verify_cert = not utils.is_true(data.get("disable_ssl_verification", False))
            timeout = 180
            resp = requests.request(
                method="POST",
                url=url,
                headers=headers,
                data=payload,
                timeout=timeout,
                verify=verify_cert,
            )
            if resp.content:
                content = resp.content.decode()

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            log.log_exception(_LOGGER, e, "Error")
            self.put_msg("Unable to reach server!")
            return False

        except ssl.SSLCertVerificationError as e:
            log.log_exception(_LOGGER, e, "SSLCertVerificationError")
            self.put_msg(
                "Error: Certificate verification failed. Please refer to splunk_ta_cisco_ucs_validation.log"
                " for more details."
            )
            return False

        except Exception as e:
            log.log_exception(
                _LOGGER,
                e,
                "Unexpected error while authenticating credentials for"
                " URL: {}, Exception-Type: {}".format(),
                url,
                type(e),
            )
            self.put_msg(
                "Unexpected error occured! Please refer to splunk_ta_cisco_ucs_validation.log"
                " for more details."
            )
            return False
        else:
            if resp.status_code not in (200, 201):
                _LOGGER.error(
                    "Response returned with status code %s, Content of the response: %s",
                    resp.status_code,
                    content,
                )
                self.put_msg(
                    "Got invalid status code: {} while authenticating!".format(
                        resp.status_code
                    )
                )
                return False
            else:
                content = defused_fromstring(content)
                if content.get("errorDescr"):
                    _LOGGER.error(
                        "Response returned with status code %s and error description: %s",
                        resp.status_code,
                        content.get("errorDescr"),
                    )
                    self.put_msg(content.get("errorDescr"))
                    return False
                elif content.get("outCookie"):
                    _LOGGER.info("Authentication successful with provided credentials.")
                    return True
                else:
                    _LOGGER.error("Unknown Error: Response=%s", content)
                    self.put_msg(
                        "Unexpected error occured! Please refer to splunk_ta_cisco_ucs_validation.log"
                        " for more details."
                    )
                    return False
