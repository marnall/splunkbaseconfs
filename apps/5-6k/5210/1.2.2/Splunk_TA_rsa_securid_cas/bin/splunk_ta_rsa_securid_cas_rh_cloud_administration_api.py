##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
import logging
import splunk.rest as rest
from solnlib import log
from solnlib.modular_input import checkpointer
from splunk_ta_rsa_securid_cas_input_validation import DateValidator, IntervalValidator
import os.path as op

logger = log.Logs().get_logger("splunk_ta_rsa_securid_cas_delete_checkpoint")
logger.setLevel("INFO")
util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default="3600",
        validator=IntervalValidator(),
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
    field.RestField(
        "account_name", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "endpoint", required=True, encrypted=False, default="adminlog", validator=None
    ),
    field.RestField(
        "startTimeAfter",
        required=False,
        encrypted=False,
        default=None,
        validator=DateValidator(),
    ),
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    "cloud_administration_api",
    model,
)


class RsaSecurIdCasExternalHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, confInfo):
        AdminExternalHandler.handleList(self, confInfo)

    def handleEdit(self, confInfo):
        AdminExternalHandler.handleEdit(self, confInfo)

    def handleCreate(self, confInfo):
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleRemove(self, confInfo):
        self.delete_checkpoint()
        AdminExternalHandler.handleRemove(self, confInfo)

    def delete_checkpoint(self):
        """Delete the checkpoint when user deletes input"""
        try:
            session_key = self.getSessionKey()
            app_name = __file__.split(op.sep)[-3]
            rest_url = "/servicesNS/nobody/{}/storage/collections/config/{}_last_event_time/".format(
                app_name, self.callerArgs.id
            )
            _, _ = rest.simpleRequest(
                rest_url,
                sessionKey=session_key,
                method="DELETE",
                getargs={"output_mode": "json"},
                raiseAllErrors=True,
            )

            logger.info(
                "Removed checkpoint for {} input".format(str(self.callerArgs.id))
            )

        except Exception as e:
            logger.error(
                "Error while deleting checkpoint for {} input. \n Error: {}".format(
                    str(self.callerArgs.id), str(e)
                )
            )


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=RsaSecurIdCasExternalHandler,
    )
