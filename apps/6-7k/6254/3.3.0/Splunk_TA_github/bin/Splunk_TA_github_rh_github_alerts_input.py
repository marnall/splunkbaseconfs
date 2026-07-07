#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from Splunk_TA_github_utils import check_required_fields
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
import logging
from Splunk_TA_github_utils import (
    GetSessionKey,
    delete_checkpoint,
    set_logger,
    ValidateAlertInput,
    StartDateValidation,
    remove_all_value_option,
)

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        "input_type",
        required=False,
        encrypted=False,
        default="GitHub Alerts Input",
        validator=None,
    ),
    field.RestField(
        "account_type", required=True, encrypted=False, default="orgs", validator=None
    ),
    field.RestField(
        "alert_type",
        required=True,
        encrypted=False,
        default="code_scanning_alerts",
        validator=None,
    ),
    field.RestField(
        "start_date",
        required=False,
        encrypted=False,
        default=None,
        validator=StartDateValidation(),
    ),
    field.RestField(
        "org_name",
        required=False,
        encrypted=False,
        default=None,
        validator=ValidateAlertInput(),
    ),
    field.RestField(
        "severity", required=False, encrypted=False, default="all", validator=None
    ),
    field.RestField(
        "enterprises_name",
        required=False,
        encrypted=False,
        default=None,
        validator=ValidateAlertInput(),
    ),
    field.RestField(
        "state",
        required=False,
        encrypted=False,
        default="all",
        validator=None,
    ),
    field.RestField(
        "account",
        required=True,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField(
        "dependabot_severity",
        required=False,
        encrypted=False,
        default="all",
        validator=None,
    ),
    field.RestField(
        "dependabot_state",
        required=False,
        encrypted=False,
        default="all",
        validator=None,
    ),
    field.RestField(
        "dependabot_ecosystem",
        required=False,
        encrypted=False,
        default="all",
        validator=None,
    ),
    field.RestField(
        "dependabot_scope",
        required=False,
        encrypted=False,
        default="all",
        validator=None,
    ),
    field.RestField(
        "secret_scanning_resolution",
        required=False,
        encrypted=False,
        default="all",
        validator=None,
    ),
    field.RestField(
        "secret_scanning_validity",
        required=False,
        encrypted=False,
        default="all",
        validator=None,
    ),
    field.RestField(
        "secret_scanning_state",
        required=False,
        encrypted=False,
        default="open",
        validator=None,
    ),
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default=300,
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^\d+$""",
            ),
            validator.Number(
                max_val=31536000,
                min_val=1,
            ),
        ),
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
    "github_alerts_input",
    model,
)


class GitHubAlertsInputHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        self.checkpoint_deleted = False
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleEdit(self, confInfo):
        input_name = self.callerArgs.id
        session_key = GetSessionKey().session_key
        _logger = set_logger(
            session_key,
            "Splunk_TA_github_alerts_input_" + input_name,
        )
        check_required_fields(self.payload)
        AdminExternalHandler.handleEdit(self, confInfo)

    def handleCreate(self, confInfo):
        """
        validates the field requirements.
        """
        check_required_fields(self.payload)
        remove_all_value_option(self.payload)
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleRemove(self, confInfo):

        input_name = self.callerArgs.id
        session_key = GetSessionKey().session_key
        _logger = set_logger(
            session_key,
            "Splunk_TA_github_alerts_input_" + input_name,
        )
        self.checkpoint_deleted = delete_checkpoint(
            _logger,
            session_key,
            "github_alerts_input://" + input_name,
        )
        if self.checkpoint_deleted:
            _logger.info(
                "Successfully deleted checkpoint for input - {}".format(input_name)
            )
            AdminExternalHandler.handleRemove(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=GitHubAlertsInputHandler,
    )
