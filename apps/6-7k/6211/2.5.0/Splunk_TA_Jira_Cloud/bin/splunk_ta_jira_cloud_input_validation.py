##
# SPDX-FileCopyrightText: 2025 Splunk LLC.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

import datetime
import re

from splunktaucclib.rest_handler.endpoint.validator import Validator
from jira_cloud_consts import JIRA_QUERY_DATE_FORMAT, JIRA_AUDIT_DATE_TIME_FORMAT

UI_FIELD_VALIDATION_MESSAGE = "For {}, values can only include lower-case letters, numbers, '$', '.' and '_' characters. Got the value: {}"  # noqa: E501
FIELD_TO_LABEL = {
    "time_field": "Time field",
    "exclude": "Excluded field",
    "include": "Included field",
}
PROJECTS_VALIDATION_MESSAGE = "For projects, values can only include upper-case letters and numbers. Got the value: {}"


class DateValidation:
    """
    Date Validation
    """

    def is_valid_date_format(self, value, date_format):
        try:
            datetime.datetime.strptime(value, date_format)
            return True
        except ValueError:
            return False

    def is_future_date(self, value, date_format):
        return value > datetime.datetime.utcnow().strftime(date_format)

    def validate_date(self, start_date, date_format):
        if not self.is_valid_date_format(start_date, date_format):
            errorMsg = (
                f"Invalid date format specified for '{self.field_name}': {start_date}"
            )
            return False, errorMsg

        if self.is_future_date(start_date, date_format):
            errorMsg = f"{self.field_name} cannot be in future"
            return False, errorMsg

        return True, ""


class JiraIssueStartDateValidation(Validator, DateValidation):
    """
    Start date Validation
    """

    def __init__(self, *args, **kwargs):
        self.field_name = "Start Date"
        super().__init__(*args, **kwargs)

    def validate(self, start_date, data):
        """
        This function validates the start_date present in the payload when saving an input
        It validates the following:
        1. Format of the start date
        2. Whether entered start date is a future date or not.
        """
        is_valid, msg = self.validate_date(start_date, JIRA_QUERY_DATE_FORMAT)
        if not is_valid:
            self.put_msg(msg)
        return is_valid


class JiraAuditStartDateValidation(Validator, DateValidation):
    """
    Start date Validation
    """

    def __init__(self, *args, **kwargs):
        self.field_name = "UTC Start Time"
        super().__init__(*args, **kwargs)

    def validate(self, start_date, data):
        """
        This function validates the start_date present in the payload when saving an input
        It validates the following:
        1. Format of the start date
        2. Whether entered start date is a future date or not.
        """
        is_valid, msg = self.validate_date(start_date, JIRA_AUDIT_DATE_TIME_FORMAT)
        if not is_valid:
            self.put_msg(msg)
        return is_valid


class SpecialValidator(Validator):
    def __init__(self, *args, **kwargs):
        # popping the name as it isn't required in Validator class
        self.name = kwargs.pop("name")
        super(SpecialValidator, self).__init__(*args, **kwargs)

    def validate(self, value_list, data):
        for value in [item.strip() for item in value_list.split(",")]:
            if re.search(r"^([a-z$_.\d]+)$", value) is None:
                self.put_msg(
                    UI_FIELD_VALIDATION_MESSAGE.format(
                        FIELD_TO_LABEL.get(self.name, "<unknown field>"), value
                    ),
                    True,
                )
                return False
        return True


class ProjectsSpecialValidator(Validator):
    def __init__(self, *args, **kwargs):
        super(ProjectsSpecialValidator, self).__init__(*args, **kwargs)

    def validate(self, value_list, data):
        for value in [item.strip() for item in value_list.split(",")]:
            if re.search(r"^([A-Z\d]+)$", value) is None:
                self.put_msg(
                    PROJECTS_VALIDATION_MESSAGE.format(value),
                    True,
                )
                return False
        return True
