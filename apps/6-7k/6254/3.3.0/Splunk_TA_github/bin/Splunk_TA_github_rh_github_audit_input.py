#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import logging

# isort: off
import import_declare_test  # noqa: F401
from Splunk_TA_github_utils import check_required_fields
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import (
    DataInputModel,
    RestModel,
    field,
    validator,
)
from Splunk_TA_github_utils import (
    GetSessionKey,
    delete_checkpoint,
    set_logger,
    ValidateAuditInput,
    StartDateValidation,
)

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        "account_type", required=True, encrypted=False, default="orgs", validator=None
    ),
    field.RestField(
        "org_name",
        required=False,
        encrypted=False,
        default=None,
        validator=ValidateAuditInput(),
    ),
    field.RestField(
        "enterprises_name",
        required=False,
        encrypted=False,
        default=None,
        validator=ValidateAuditInput(),
    ),
    field.RestField(
        "use_existing_checkpoint",
        required=False,
        encrypted=False,
        default="yes",
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
        "events_type", required=True, encrypted=False, default="web", validator=None
    ),
    field.RestField(
        "account", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.Number(
                max_val=31536000,
                min_val=1,
            ),
            validator.Pattern(
                regex=r"""^\d+$""",
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
    field.RestField(
        "input_type",
        required=False,
        encrypted=False,
        default="GitHub Audit Input",
        validator=None,
    ),
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    "github_audit_input",
    model,
)


class GitHubAuditInputHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        self.checkpoint_deleted = False
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, confInfo):
        AdminExternalHandler.handleList(self, confInfo)

    def handleEdit(self, confInfo):
        check_required_fields(self.payload)
        # delete checkpoint if user want to reset checkpoint in edit mode
        if self.payload.get("use_existing_checkpoint") == "0":
            self.delete_checkpoint()
        if "use_existing_checkpoint" in self.payload:
            del self.payload["use_existing_checkpoint"]
        AdminExternalHandler.handleEdit(self, confInfo)

    def handleCreate(self, confInfo):
        check_required_fields(self.payload)
        if "use_existing_checkpoint" in self.payload:
            del self.payload["use_existing_checkpoint"]
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleRemove(self, confInfo):
        self.delete_checkpoint()
        AdminExternalHandler.handleRemove(self, confInfo)

    def delete_checkpoint(self):
        """
        Delete the checkpoint when user deletes input
        """
        input_name = self.callerArgs.id
        session_key = GetSessionKey().session_key
        _logger = set_logger(
            session_key,
            "Splunk_TA_github_audit_input_" + input_name,
        )
        self.checkpoint_deleted = delete_checkpoint(
            _logger,
            session_key,
            "github_audit_input://" + input_name,
        )
        if self.checkpoint_deleted:
            _logger.info(
                "Successfully deleted checkpoint for input - {}".format(input_name)
            )


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=GitHubAuditInputHandler,
    )
