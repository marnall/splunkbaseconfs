#
# SPDX-FileCopyrightText: 2025 Splunk LLC.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import import_declare_test
import datetime
import logging
import splunk.rest as rest
import jira_cloud_utils as utils
import jira_cloud_consts as jcc
from jira_cloud_checkpoint import JiraCloudCheckpoint as Checkpoint
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError

from splunk_ta_jira_cloud_input_validation import (
    JiraIssueStartDateValidation,
    SpecialValidator,
    ProjectsSpecialValidator,
)

util.remove_http_proxy_env_vars()

fields = [
    field.RestField(
        "api_token", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "projects",
        required=True,
        encrypted=False,
        default=None,
        validator=ProjectsSpecialValidator(),
    ),
    field.RestField(
        "start_date",
        required=False,
        encrypted=False,
        default="",
        validator=JiraIssueStartDateValidation(),
    ),
    field.RestField(
        "use_existing_checkpoint",
        required=False,
        encrypted=False,
        default="yes",
        validator=None,
    ),
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default=300,
        validator=validator.Number(
            max_val=86400,
            min_val=60,
        ),
    ),
    field.RestField(
        "include",
        required=False,
        encrypted=False,
        default=None,
        validator=SpecialValidator(name="include"),
    ),
    field.RestField(
        "exclude",
        required=False,
        encrypted=False,
        default=None,
        validator=SpecialValidator(name="exclude"),
    ),
    field.RestField(
        "time_field",
        required=False,
        encrypted=False,
        default="updated",
        validator=SpecialValidator(name="time_field"),
    ),
    field.RestField(
        "filter_data",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=1000,
            min_len=0,
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
    "jira_cloud_issues_input",
    model,
)


class JiraCloudExternalHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, conf_info):
        AdminExternalHandler.handleList(self, conf_info)

    def handleCreate(self, conf_info):
        if "use_existing_checkpoint" in self.payload:
            del self.payload["use_existing_checkpoint"]
        self.set_start_date()
        AdminExternalHandler.handleCreate(self, conf_info)

    def set_start_date(self):
        """
        This function gets start date from the user input.
        If no start date is specified, then it takes current UTC time -30 days,
        and adds it in the payload so that it gets stored in inputs.conf
        """
        now = datetime.datetime.utcnow() - datetime.timedelta(days=30)
        date_format = "%Y-%m-%d %H:%M"
        start_date = self.payload.get("start_date")
        if not start_date:
            datetime_now = datetime.datetime.strftime(now, date_format)
            self.payload["start_date"] = datetime_now

    def handleEdit(self, conf_info):
        if self.payload.get("use_existing_checkpoint") == "no":
            self.delete_checkpoint()
        if "use_existing_checkpoint" in self.payload:
            del self.payload["use_existing_checkpoint"]
        AdminExternalHandler.handleEdit(self, conf_info)

    def handleRemove(self, conf_info):
        self.delete_checkpoint()
        AdminExternalHandler.handleRemove(self, conf_info)

    def delete_checkpoint(self):
        """
        Delete the checkpoint when user deletes input
        """
        session_key = self.getSessionKey()
        logfile_name = jcc.LOG_FILE_PREFIX + self.callerArgs.id
        logger = utils.set_logger(session_key, logfile_name)
        try:
            self.checkpoint = Checkpoint(
                logger=logger,
                input_name=jcc.COLLECTION_NAME,
                session_key=session_key,
            )
            self.checkpoint.delete_checkpoint(self.callerArgs.id)
        except Exception as e:
            msg = "Error while deleting checkpoint for {} input. Error: {}".format(
                self.callerArgs.id, e
            )
            utils.add_ucc_error_logger(
                logger=logger,
                logger_type=jcc.GENERAL_EXCEPTION,
                exception=e,
                exc_label=jcc.UCC_EXCEPTION_EXE_LABEL.format(
                    "splunk_ta_jira_cloud_rh_jira_cloud_issue_input"
                ),
                msg_before=msg,
            )
            raise RestError(
                500,
                "Error while deleting checkpoint for {} input.".format(
                    self.callerArgs.id
                ),
            )


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=JiraCloudExternalHandler,
    )
