##
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

import datetime
from splunktaucclib.rest_handler.endpoint.validator import Validator


class StartDateValidation(Validator):
    """
    Start date Validation
    """

    def __init__(self, *args, **kwargs):
        super(StartDateValidation, self).__init__(*args, **kwargs)

    def validate(self, value, data):
        """
        This function validates the start_date present in the payload when saving an input
        It validates the following:
        1. Format of the start date
        2. Whether entered start date is a future date or not.
        """
        start_date = data.get("start_date")
        today = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        if start_date:
            try:
                datetime.datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                errorMsg = "Invalid date format specified for 'Start Date'"
                self.put_msg(errorMsg)
                return False
            if start_date > today:
                errorMsg = "Start date cannot be in future"
                self.put_msg(errorMsg)
                return False
            elif start_date <= today:
                return True
