import ta_cisco_cybervision_declare # noqa
import os
import datetime
from splunktaucclib.rest_handler.endpoint.validator import Validator


class ValidateStartDate(Validator):
    """Class to validate start date field."""

    def __init__(self, *args, **kwargs):
        """:param validator: user-defined validating function."""
        super(ValidateStartDate, self).__init__()
        self.my_app = __file__.split(os.sep)[-3]

    def validate(self, value, data):
        """This method validates the start date field."""
        start_date = data["start_date"]
        try:
            formatted_start_date = datetime.datetime.strptime(
                start_date, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            msg = "Please enter correct UTC date of format('YYYY-MM-DDTHH:MM:SSZ)"
            self.put_msg(msg)
            return False
        if (formatted_start_date >= datetime.datetime.utcnow()):
            msg = "Please enter start date less than current date time."
            self.put_msg(msg)
            return False
        else:
            return True
