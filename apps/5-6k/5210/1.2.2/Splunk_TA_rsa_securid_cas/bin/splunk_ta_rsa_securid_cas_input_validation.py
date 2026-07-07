##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
from splunktaucclib.rest_handler.endpoint.validator import Validator
from solnlib import log
from rsa_utils import validate_start_date

logger = log.Logs().get_logger("splunk_ta_rsa_securid_cas_input_validation")
logger.setLevel("INFO")


class DateValidator(Validator):
    """
    This class validates if the date passed for validation
     in input is valid or not.
    If it is invalid then throws error in UI and logs
    """

    def __init__(self, *args, **kwargs):
        super(DateValidator, self).__init__(*args, **kwargs)

    def validate(self, value, data):
        try:
            validate_start_date(value)

        except Exception as exc:
            self.put_msg(str(exc), True)
            logger.error("{} , but got '{}'".format(exc, value))
            return False

        return True


class IntervalValidator(Validator):
    """
    This class validates if the interval passed for validation
     in input is valid or not.
    If it is invalid then throws error in UI and logs
    """

    def validate(self, value, data):
        """We define Custom validation here for verifying interval field"""
        endpoint = data.get("endpoint")
        interval = int(data.get("interval"))

        try:
            if endpoint == "/v2/users/highrisk" and interval < 1:
                self.put_msg(
                    "Interval must be a positive integer greater than or equal to 1",
                    True,
                )
                return False
            elif endpoint != "/v2/users/highrisk" and (
                interval < 1 or interval > 86400
            ):
                self.put_msg(
                    "Interval must be a positive integer from 1 to 86400", True
                )
                return False
            else:
                return True
        except Exception:
            self.put_msg("Internal exception occured. Please try again", True)
            return False
