import ta_purestorage_unified_declare  # noqa:   401

import os
import datetime
import re
from splunktaucclib.rest_handler.endpoint.validator import Validator, String


class ValidateStartDate(Validator):
    """Description: Validator for Start Date."""

    def __init__(self, *args, **kwargs):
        """
        Start date validator constructor.

        :param validator: user-defined validating function
        """
        super(ValidateStartDate, self).__init__()
        self.my_app = __file__.split(os.sep)[-3]

    def validate(self, value, data):
        """Validation method."""
        start_date = data["start_date"]
        try:
            formatted_start_date = datetime.datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            msg = "Please enter correct UTC date of format('YYYY-MM-DDTHH:mm:ssZ)"
            self.put_msg(msg)
            return False
        if (formatted_start_date >= datetime.datetime.utcnow()):
            msg = "Please enter start date less than current date time."
            self.put_msg(msg)
            return False
        else:
            return True


class ValidateInterval(Validator):
    """Description: Validator for Interval."""

    def __init__(self, regex):
        """
        Interval validator constructor.

        user-defined interval validating function
        """
        super(ValidateInterval, self).__init__()
        self._regexp = re.compile(regex)

    def validate(self, value, data):
        """Validation method."""
        if not self._regexp.match(value):
            msg = "Interval must be an integer."
            self.put_msg(msg)
            return False
        if data.get("input_type") == "pure1" and not (int(value) >= 3600):
            msg = 'Interval should be greater than or equal to 3600 seconds.'
            self.put_msg(msg)
            return False
        if not (int(value) >= 60):
            msg = 'Interval should be greater than or equal to 60 seconds.'
            self.put_msg(msg)
            return False
        return True


class ValidateIndexLength(String):
    """Description: Validator for Index length."""

    def validate(self, value, data):
        """Validation method."""
        str_len = len(value)
        if str_len < self._min_len or str_len > self._max_len:
            msg = " Length of index name should be between {} and {}.".format(
                self._min_len, self._max_len)
            self.put_msg(msg)
            return False
        return True
