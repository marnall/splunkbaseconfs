#
# SPDX-FileCopyrightText: 2025 Splunk LLC.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import logging

import import_declare_test  # noqa: 401
from splunk_ta_jira_cloud_validation import Validator
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import (
    RestModel,
    SingleModel,
    field,
    validator,
)
from splunktaucclib.rest_handler.error import RestError
import jira_cloud_utils as utils
import jira_cloud_consts as jcc

util.remove_http_proxy_env_vars()
APP_NAME = import_declare_test.ta_name

fields = [
    field.RestField(
        "domain", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "username",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z0-9.!#$%&'*+\/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$""",  # noqa: E501
        ),
    ),
    field.RestField(
        "token", required=True, encrypted=True, default=None, validator=None
    ),
    field.RestField(
        "help_link", required=False, encrypted=False, default=None, validator=None
    ),
]
model = RestModel(fields, name=None)


endpoint = SingleModel("splunk_ta_jira_cloud_api_token", model, config_name="api_token")


class JiraCloudApiTokenExternalHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def _callValidator(self):
        Validator(session_key=self.getSessionKey()).validate_token(
            domain=self.payload.get("domain"),
            username=self.payload.get("username"),
            token=self.payload.get("token"),
        )

    def handleEdit(self, confInfo):
        self._callValidator()
        AdminExternalHandler.handleEdit(self, confInfo)

    def handleCreate(self, confInfo):
        self._callValidator()
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleRemove(self, confInfo):
        session_key = self.getSessionKey()
        account_name = self.callerArgs.id
        logger = utils.set_logger(session_key, jcc.JIRA_CLOUD_VALIDATION)
        try:
            res = utils.get_conf_details(session_key, logger, jcc.INPUTS_CONFIG_FILE)
            for input_name, input_props in res.items():
                if (
                    input_props["eai:appName"] == APP_NAME
                    and input_props.get("api_token", "") == account_name
                ):
                    raise RestError(
                        409,
                        "Cannot delete the account as it is already been used in {}.".format(
                            input_name.split("//")[1]
                        ),
                    )
        except Exception as e:
            msg = "Cannot delete the account as it is already been used in {}.".format(
                input_name.split("//")[1]
            )
            utils.add_ucc_error_logger(
                logger=logger,
                logger_type=jcc.GENERAL_EXCEPTION,
                exception=e,
                exc_label=jcc.UCC_EXCEPTION_EXE_LABEL.format(
                    "splunk_ta_jira_cloud_rh_api_token"
                ),
                msg_before=msg,
            )
            raise RestError(
                409,
                "Cannot delete the account as it is already been used in {}.".format(
                    input_name.split("//")[1]
                ),
            )
        AdminExternalHandler.handleRemove(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=JiraCloudApiTokenExternalHandler,
    )
