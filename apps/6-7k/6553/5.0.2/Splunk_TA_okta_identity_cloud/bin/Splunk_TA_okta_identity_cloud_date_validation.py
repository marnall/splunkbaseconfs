##
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

import datetime
from constant import DATE_TIME_FORMAT

from splunktaucclib.rest_handler.endpoint.validator import Validator


class DateValidation:
    """
    Date Validation
    """

    def is_valid_date_format(self, value):
        try:
            datetime.datetime.strptime(value, DATE_TIME_FORMAT)
            return True
        except ValueError:
            return False

    def is_future_date(self, value):
        return value > datetime.datetime.utcnow().strftime(DATE_TIME_FORMAT)

    def validate_date(self, value):
        if not self.is_valid_date_format(value):
            errorMsg = f"Invalid {self.field_name} format specified"
            return False, errorMsg

        if self.is_future_date(value):
            errorMsg = f"{self.field_name} cannot be in future"
            return False, errorMsg

        return True, ""


class StartDateValidation(Validator, DateValidation):
    def __init__(self, *args, **kwargs):
        self.field_name = "Start Date"
        super().__init__(*args, **kwargs)

    def validate(self, value, data):
        """
        This function validates the value present in the payload when saving an input
        It validates the following:
        1. Format of the date
        2. Whether entered date is a future date or not.
        """
        # perform validation for start date
        is_valid, msg = self.validate_date(value)
        if not is_valid:
            self.put_msg(msg)
        return is_valid


class EndDateValidation(Validator, DateValidation):
    def __init__(self, *args, **kwargs):
        self.field_name = "End Date"
        super().__init__(*args, **kwargs)

    def validate(self, value, data):
        """
        This function validates the value present in the payload when saving an input
        It validates the following:
        1. Format of the date
        2. Whether entered date is a future date or not.
        3. Whether entered date is less than equal to start_date.
        """
        # perform validation for end date
        is_valid, msg = self.validate_date(value)
        if is_valid:
            if value <= data.get("start_date"):
                msg = "End date cannot be less than or equal to start date"
                self.put_msg(msg)
                return False
        else:
            self.put_msg(msg)
        return is_valid
