#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test  # isort: skip # noqa F401
import logging
import os

import box_utility
from solnlib import conf_manager, log
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler


util.remove_http_proxy_env_vars()

_LOGGER = log.Logs().get_logger("ta_box_file_ingestion")


fields = [
    field.RestField(
        "account", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "rest_endpoint",
        required=True,
        encrypted=False,
        default="folders",
        validator=None,
    ),
    field.RestField(
        "file_or_folder_id",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^\d+$""",
        ),
    ),
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default=120,
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
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    "box_file_ingestion_service",
    model,
)


class BoxFileIngestionServiceHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)
        cfm = conf_manager.ConfManager(
            self.getSessionKey(),
            import_declare_test.ta_name,
            realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(  # noqa: E501
                import_declare_test.ta_name, import_declare_test.SETTINGS_CONF
            ),
        )
        logging = cfm.get_conf(import_declare_test.SETTINGS_CONF).get("logging")
        _LOGGER.setLevel(logging.get("loglevel", "INFO"))

    def deleteCheckpoint(self, ckpt_name):
        session_key = self.getSessionKey()
        checkpoint_dir = os.path.join(
            os.path.normpath(os.environ["SPLUNK_HOME"]),
            "var",
            "lib",
            "splunk",
            "modinputs",
            "box_file_ingestion_service",
        )
        collection_name = import_declare_test.FILE_INGESTION_CHECKPOINTER
        box_utility.delete_existing_checkpoint(
            ckpt_name,
            False,
            session_key,
            checkpoint_dir,
            collection_name,
            _LOGGER,
        )

    def handleList(self, confInfo):
        AdminExternalHandler.handleList(self, confInfo)

    def handleEdit(self, confInfo):
        AdminExternalHandler.handleEdit(self, confInfo)

    def handleCreate(self, confInfo):
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleRemove(self, confInfo):
        input_name = self.callerArgs.id
        self.deleteCheckpoint(input_name)
        _LOGGER.debug(
            "Successfully deleted checkpoint for input: {}".format(input_name)
        )
        AdminExternalHandler.handleRemove(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=BoxFileIngestionServiceHandler,
    )
