"""Module for validating and processing datetime values in the XM Cyber Splunk app."""
import import_declare_test  # noqa: F401
from splunktaucclib.rest_handler.endpoint import validator
from import_declare_test import ta_prefix
from log_helper import setup_logging
import re
from datetime import datetime, timedelta


class DateTimeValidator(validator.Validator):
    """A class for validating and processing datetime values."""

    def __init__(self, *args, **kwargs):
        """Initialize the DateTimeValidator."""
        super(DateTimeValidator, self).__init__(*args, **kwargs)
        self.logger = setup_logging(f"{ta_prefix}_audit_trail_validator")

    def validate(self, value, data):
        """Validate if the given string is a valid datetime.

        Args:
            date_text (str): The datetime string to validate.

        Returns:
            bool: True if the string is a valid datetime, False otherwise.
        """
        pattern = r'^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d\.\d{3}Z$'
        format_string = '%Y-%m-%dT%H:%M:%S.%fZ'
        current_time = datetime.now()

        if not value:
            self.logger.error("Datetime string is empty.")
            self.put_msg("Datetime string is empty.")
            return False
        if not re.match(pattern, value):
            self.logger.error("Invalid format. Use YYYY-MM-DDTHH:MM:SS.SSSZ.")
            self.put_msg("Invalid format. Use YYYY-MM-DDTHH:MM:SS.SSSZ.")
            return False

        try:
            parsed_datetime = datetime.strptime(value, format_string)
        except ValueError as e:
            self.logger.error(f"Invalid datetime: {str(e)}.")
            self.put_msg(f"Invalid datetime: {str(e)}.")
            return False

        if parsed_datetime > current_time:
            self.logger.error("Datetime should not be in the future.")
            self.put_msg("Datetime should not be in the future.")
            return False

        minimum_date = current_time - timedelta(days=90)
        minimum_date = minimum_date.replace(hour=0, minute=0, second=0, microsecond=0)
        if parsed_datetime < minimum_date:
            cutoff_date = minimum_date.strftime(format_string)[:-4] + "Z"
            self.logger.error(f"Datetime should not be earlier than {cutoff_date}")
            self.put_msg(f"Datetime should not be earlier than {cutoff_date}")
            return False
        return True
