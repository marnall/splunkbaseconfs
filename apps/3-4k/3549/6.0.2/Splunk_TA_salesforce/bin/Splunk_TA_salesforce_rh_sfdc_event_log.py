#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""
This file contains certain ignores for certain linters.

* isort ignores:
- isort: skip = Particular import must be the first import or it is conflicting with the black linter formatting.

* flake8 ignores:
- noqa: F401 -> Def = module imported but unused
    Reason for ignoring = This is necessary as it contains adding a path to sys.path
"""
from typing import Dict, Any

import import_declare_test  # isort: skip # noqa: F401

import logging
from datetime import datetime, timedelta

import sfdc_utility as su
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import (
    DataInputModel,
    RestModel,
    field,
    validator,
)

from Splunk_TA_salesforce_input_validation import DateValidator
from Splunk_TA_salesforce_rh_account_validation import account_validation

util.remove_http_proxy_env_vars()

special_fields = [
    field.RestField(
        "name",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.String(
                max_len=100,
                min_len=1,
            ),
            validator.Pattern(
                regex=r"""^[a-zA-Z]\w*$""",
            ),
        ),
    )
]

fields = [
    field.RestField(
        "account", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "monitoring_interval",
        required=True,
        encrypted=False,
        default="Daily",
        validator=validator.Enum(
            ("Daily", "Hourly"),
        ),
    ),
    field.RestField(
        "start_date",
        required=False,
        encrypted=False,
        default=None,
        validator=DateValidator(
            logfile="splunk_ta_salesforce_rh_sfdc_event_log", input_type="eventlog"
        ),
    ),
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Number(max_val=31536000, min_val=1, is_int=True),
    ),
    field.RestField(
        "index",
        required=True,
        encrypted=False,
        default="default",
        validator=validator.String(
            max_len=80,
            min_len=1,
        ),
    ),
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    "sfdc_event_log",
    model,
)


class SfdcEventLogExternalHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)
        self.sfdc_util_ob = su.SFDCUtil(
            log_file="splunk_ta_salesforce_rh_sfdc_event_log",
            session_key=self.getSessionKey(),
        )

    def checkStartDate(self):
        now = datetime.utcnow() - timedelta(30)
        # Check if start_date field is empty.
        # If so, set its default value to one month ago so that it gets reflected in UI.
        if not self.payload.get("start_date"):
            self.payload["start_date"] = datetime.strftime(
                now, "%Y-%m-%dT%H:%M:%S.000z"
            )

    def handleEdit(self, confInfo: Dict[str, Any]) -> None:
        if not self.payload.get("disabled"):
            account_validation(self.sfdc_util_ob, self.payload["account"])
        self.checkStartDate()
        AdminExternalHandler.handleEdit(self, confInfo)

    def handleCreate(self, confInfo: Dict[str, Any]) -> None:
        account_validation(self.sfdc_util_ob, self.payload["account"])
        self.checkStartDate()
        AdminExternalHandler.handleCreate(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=SfdcEventLogExternalHandler,
    )
