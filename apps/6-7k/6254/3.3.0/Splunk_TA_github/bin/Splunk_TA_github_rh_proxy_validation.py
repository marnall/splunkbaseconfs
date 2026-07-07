#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import re
from splunktaucclib.rest_handler.endpoint.validator import Validator
from solnlib import log
import ipaddress


class ProxyURLValidation(Validator):
    """
    Validate Proxy URL
    """

    def __init__(self, *args, **kwargs):
        self.logger = log.Logs().get_logger("Splunk_TA_github_rh_proxy_validation")
        super(ProxyURLValidation, self).__init__(*args, **kwargs)

    def validate(self, value, data):

        self.logger.debug("Verifying Proxy URL for GitHub instance {}.".format(value))

        if len(value) not in range(1, 4096):
            msg = "Invalid URL {} provided. Please ensure the URL is within length range of 1 to 4096 characters.".format(
                value
            )
            self.logger.error(msg)
            self.put_msg(msg, True)
            return False

        proxy_url_pattern = r"^[a-zA-Z0-9:][a-zA-Z0-9\.\-:]+$"
        if re.match(proxy_url_pattern, value) or (
            (value.startswith("[") and value.endswith("]"))
            and self.is_ipv6(value.strip("[]"))
        ):
            self.logger.debug("Provided Proxy URL {} is valid.".format(value))
            return True
        else:
            msg = "Invalid URL {} provided.".format(value)
            self.logger.error(msg)
            self.put_msg(msg, True)
            return False

    def is_ipv6(self, ipv6_address):
        try:
            ipaddress.IPv6Address(ipv6_address)
            self.logger.debug("proxy_url contains IPv6 address.")
            return True
        except ipaddress.AddressValueError as e:
            log.log_connection_error(
                self.logger,
                e,
                msg_before="Not a valid IPv6 address: {}.".format(ipv6_address),
            )
            return False


class ProxyValidation(Validator):
    """
    Validate Proxy details provided
    """

    def __init__(self, *args, **kwargs):
        super(ProxyValidation, self).__init__(*args, **kwargs)

    def validate(self, value, data):
        username_val = data.get("proxy_username")
        password_val = data.get("proxy_password")

        # If password is specified, then username is required
        if password_val and not username_val:
            self.put_msg(
                "Username is required if password is specified", high_priority=True
            )
            return False
        # If username is specified, then password is required
        elif username_val and not password_val:
            self.put_msg(
                "Password is required if username is specified", high_priority=True
            )
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
                self.put_msg(msg, high_priority=True)
                return False

        if password_val:
            str_len = len(password_val)
            _min_len = 1
            _max_len = 8192
            if str_len < _min_len or str_len > _max_len:
                msg = (
                    "String length of password should be between %(min_len)s and %(max_len)s"
                    % {"min_len": _min_len, "max_len": _max_len}
                )
                self.put_msg(msg, high_priority=True)
                return False

        return True
