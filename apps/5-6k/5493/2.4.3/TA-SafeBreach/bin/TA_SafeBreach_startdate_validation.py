"""This file validates start date time."""
import os
import datetime

from splunktaucclib.rest_handler.endpoint.validator import Validator
import ta_safebreach_const


class ValidateStartDate(Validator):
    """Validate start date time class."""

    def __init__(self, *args, **kwargs):
        """:param validator: user-defined validating function."""
        super(ValidateStartDate, self).__init__()
        self.my_app = __file__.split(os.sep)[-3]

    def validate(self, value, data):
        """Validate start date and time."""
        start_date = data["start_date_time"]
        try:
            formatted_start_date = datetime.datetime.strptime(
                start_date, ta_safebreach_const.START_DATETIME_FORMAT
            )
        except ValueError:
            msg = "Please enter correct UTC date of format('YYYY-MM-DDTHH:MM:SS.SSSZ)."
            self.put_msg(msg)
            return False
        if formatted_start_date >= datetime.datetime.utcnow():
            msg = "Please enter Start DateTime less than current DateTime."
            self.put_msg(msg)
            return False
        else:
            return True
