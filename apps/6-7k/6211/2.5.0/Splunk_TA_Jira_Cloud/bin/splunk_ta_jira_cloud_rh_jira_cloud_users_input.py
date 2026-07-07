#
# SPDX-FileCopyrightText: 2025 Splunk LLC.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import logging

import import_declare_test  # noqa
import jira_cloud_consts as jcc
import jira_cloud_utils as utils
import splunk.rest as rest
from jira_cloud_checkpoint import JiraCloudCheckpoint as Checkpoint
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import (
    DataInputModel,
    RestModel,
    field,
    validator,
)
from splunktaucclib.rest_handler.error import RestError

util.remove_http_proxy_env_vars()


special_fields = [
    field.RestField(
        "name",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^[a-zA-Z]\w*$""",
            ),
            validator.String(
                max_len=100,
                min_len=1,
            ),
        ),
    )
]

fields = [
    field.RestField(
        "api_token",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.String(
                max_len=50,
                min_len=1,
            ),
            validator.Pattern(
                regex=r"""^[a-zA-Z]\w*$""",
            ),
        ),
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
        default=86400,
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^((?:-1|\d+(?:\.\d+)?)|(([\*\d{1,2}\,\-\/]+\s){4}[\*\d{1,2}\,\-\/]+))$""",
            ),
            validator.Number(
                max_val=604800,
                min_val=10,
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
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = DataInputModel(
    "jira_cloud_users_input",
    model,
)


class JiraCloudUsersExternalHandler(AdminExternalHandler):
    """
    This class contains methods related to Checkpointing
    """

    def __init__(self, *args, **kwargs):
        admin_external.AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, conf_info):
        admin_external.AdminExternalHandler.handleList(self, conf_info)

    def handleEdit(self, conf_info):
        if self.payload.get("use_existing_checkpoint") == "no":
            self.delete_checkpoint()
        if "use_existing_checkpoint" in self.payload:
            del self.payload["use_existing_checkpoint"]
        admin_external.AdminExternalHandler.handleEdit(self, conf_info)

    def handleCreate(self, conf_info):
        if "use_existing_checkpoint" in self.payload:
            del self.payload["use_existing_checkpoint"]
        admin_external.AdminExternalHandler.handleCreate(self, conf_info)

    def handleRemove(self, conf_info):
        self.delete_checkpoint()
        admin_external.AdminExternalHandler.handleRemove(self, conf_info)

    def delete_checkpoint(self):
        """
        Delete the checkpoint when user deletes input
        """
        session_key = self.getSessionKey()
        logfile_name = jcc.JIRA_CLOUD_USERS_LOGFILE_PREFIX + self.callerArgs.id
        logger = utils.set_logger(session_key, logfile_name)
        try:
            self.checkpoint = Checkpoint(
                logger=logger,
                input_name=jcc.KVSTORE_USERS_COLLECTION_NAME,
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
                    "splunk_ta_jira_cloud_rh_jira_cloud_users_input"
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
        handler=JiraCloudUsersExternalHandler,
    )
