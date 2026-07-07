#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
from typing import Dict, Any

import sfdc_utility as su

from datetime import datetime, timedelta
from splunktaucclib.rest_handler.endpoint.validator import Validator
import splunk.admin as admin
from solnlib import log


class GetSessionKey(admin.MConfigHandler):
    def __init__(self):
        self.session_key = self.getSessionKey()


class DateValidator(Validator):
    """
    This class validates if the date passed for validation
    in input is in future.
    If so throws error in UI and logs
    """

    def __init__(self, *args, **kwargs):
        self.logfile = kwargs.pop("logfile")
        self.input_type = kwargs.pop("input_type")
        super(DateValidator, self).__init__(*args, **kwargs)

    def validate(self, value: str, data: Dict[str, Any]) -> bool:
        try:
            self.sfdc_util_ob = su.SFDCUtil(
                log_file=self.logfile, session_key=GetSessionKey().session_key
            )

            delay = int(data.get("delay", "0"))
            input_date = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.000z")
            now = datetime.utcnow()
            if input_date > (now - timedelta(seconds=delay)):
                if self.input_type == "object":
                    self.put_msg(
                        "Start date should not be in future with respect to the delay provided. i.e start_date <= current_utctime - delay",
                        True,
                    )
                else:
                    self.put_msg("Start date should not be in future", True)
                log.log_configuration_error(
                    self.sfdc_util_ob.logger,
                    Exception("Date Validation Error"),
                    msg_before="Start date of the input should not be in future, but got '{value}'",
                )

                return False
        except ValueError as ve:
            self.put_msg(
                "The provided date does not match format '%Y-%m-%dT%H:%M:%S.000z'", True
            )
            log.log_exception(
                self.sfdc_util_ob.logger,
                ve,
                "Validation VakueError",
                msg_before=f"Start Date of the input should be in %Y-%m-%dT%H:%M:%S.000z format, but got '{value}'",
            )
            return False
        except Exception as e:
            self.put_msg(f"Error occured while saving the Input: {e}", True)
            log.log_exception(
                self.sfdc_util_ob.logger,
                e,
                "Validation Error",
                msg_before=f"Error occured while saving the Input: {e}",
            )
            return False
        return True
