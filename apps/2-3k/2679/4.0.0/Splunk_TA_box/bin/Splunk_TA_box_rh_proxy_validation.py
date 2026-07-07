#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from splunktaucclib.rest_handler.endpoint.validator import Validator
import re


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


class ProxyURLValidation(Validator):
    """
    Validate Proxy ServiceNow URL
    """

    def __init__(self, *args, **kwargs):
        super(ProxyURLValidation, self).__init__(*args, **kwargs)

    def validate(self, value, data):
        self.put_msg("Verifying Proxy URL {}.".format(value))
        str_len = len(value)
        _min_len = 1
        _max_len = 4096

        proxy_url_pattern = r"^[a-zA-Z0-9:][a-zA-Z0-9\.\-:]+$"
        if re.match(proxy_url_pattern, value) and (0 < len(value) < 4096):
            self.put_msg("Provided Proxy URL {} is valid.".format(value))
            return True
        elif str_len < _min_len or str_len > _max_len:
            msg = "String should be shorter than 4096"
            self.put_msg(msg, high_priority=True)
            return False
        else:
            msg = "Not matching the pattern: {}".format(value)
            self.put_msg(msg, high_priority=True)
            return False
