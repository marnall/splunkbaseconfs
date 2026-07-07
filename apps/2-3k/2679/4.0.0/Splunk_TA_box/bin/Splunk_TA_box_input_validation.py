#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import logging
from datetime import datetime

from splunktaucclib.rest_handler.endpoint.validator import Validator

APP_NAME = "Splunk_TA_box"
_LOGGER = logging.getLogger("ta_box")


class DateValidator(Validator):
    """
    This class validates if the data passed for validation in input is in future.
    If so throws error in UI and logs.
    """

    def __init__(self, *args, **kwargs):
        super(DateValidator, self).__init__(*args, **kwargs)

    def validate(self, value, data):
        try:
            input_date = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
            now = datetime.utcnow()
            if input_date > now:
                self.put_msg("Start date should not be in future", True)
                _LOGGER.error(
                    "Start date of the input should not be in future, but got '{}'".format(
                        value
                    )
                )
                return False

        except ValueError:
            self.put_msg(
                "The provided date does not match format '%Y-%m-%dT%H:%M:%S'", True
            )
            _LOGGER.error(
                "Start Date of the input should be in YYYY-DD-MMThh:mm:ss format, but got '{}'".format(
                    value
                )
            )
            return False

        return True
