"""Validation code for account host name, account credentials and proxy settings."""

import traceback

from splunktaucclib.rest_handler.endpoint.validator import Validator
import splunk.admin as admin

from common import log
import time
import datetime

logger = log.get_logger(__name__)


class GetSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()


class ValidateInputParams(Validator):
    """This class validates the input_start_time parameter."""

    def validate(self, value, data):
        """Validating input_start_time based on historical value."""
        try:
            start_time = time.time()
            if data.get("historical_data") == "0":
                start_date_time = datetime.datetime.fromtimestamp(start_time)
                formatted_input_start_time = start_date_time.strftime("%Y-%m-%d %H:%M:%S")
                data["input_start_time"] = formatted_input_start_time
            else:
                delta = 24 * 60 * 60
                new_start_time = start_time - delta
                start_date_time = datetime.datetime.fromtimestamp(new_start_time)
                formatted_input_start_time = start_date_time.strftime("%Y-%m-%d %H:%M:%S")
                data["input_start_time"] = formatted_input_start_time
            return True
        except Exception as e:
            msg = "Unrecognized error: {}".format(str(e))
            logger.error(msg)
            self.put_msg(msg)
            logger.error(traceback.format_exc())
            return False
