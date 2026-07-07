#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test  # isort: skip # noqa F401
import logging
import os

import box_utility
from checkpoint import Checkpointer
from solnlib import conf_manager, log
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import (
    DataInputModel,
    RestModel,
    field,
    validator,
)

util.remove_http_proxy_env_vars()

_LOGGER = log.Logs().get_logger("ta_box_live_monitor")

fields = [
    field.RestField(
        "account",
        required=True,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField(
        "rest_endpoint",
        required=True,
        encrypted=False,
        default="events",
        validator=None,
    ),
    field.RestField(
        "reuse_checkpoint",
        required=False,
        encrypted=False,
        default="yes",
        validator=None,
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
                is_int=True,
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
    field.RestField(
        "disabled",
        required=False,
        validator=None,
    ),
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    "box_live_monitoring_service",
    model,
)


class BoxLiveMonitoringServiceHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)
        cfm = conf_manager.ConfManager(
            self.getSessionKey(),
            "Splunk_TA_box",
            realm="__REST_CREDENTIAL__#Splunk_TA_box#configs/conf-splunk_ta_box_settings",
        )
        logging = cfm.get_conf("splunk_ta_box_settings").get("logging")
        _LOGGER.setLevel(logging.get("loglevel", "INFO"))

    def deleteCheckpoint(self, ckpt_name):
        session_key = self.getSessionKey()
        checkpoint_dir = os.path.join(
            os.path.normpath(os.environ["SPLUNK_HOME"]),
            "var",
            "lib",
            "splunk",
            "modinputs",
            "box_live_monitoring_service",
        )
        collection_name = import_declare_test.LIVE_MONITORING_EVENTS_CHECKPOINTER
        use_state_store = False
        box_utility.delete_existing_checkpoint(
            ckpt_name,
            use_state_store,
            session_key,
            checkpoint_dir,
            collection_name,
            _LOGGER,
        )

    def checkReuseCheckpoint(self):
        # Check the reuse_checkpoint field. If it's value is 'no', delete it's checkpoint if present.
        if self.payload.get("reuse_checkpoint") == "no":
            ckpt_name = self.callerArgs.id
            _LOGGER.info(
                "The reuse_checkpoint field is found to be No for input {}, Hence the existing checkpoint "
                "will be deleted and the Data will be ingested using stream position 0.".format(
                    ckpt_name
                )
            )
            self.deleteCheckpoint(ckpt_name)

        if "reuse_checkpoint" in self.payload:
            del self.payload["reuse_checkpoint"]

    def handleCreate(self, confInfo):
        self.checkReuseCheckpoint()
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleEdit(self, confInfo):
        self.checkReuseCheckpoint()
        AdminExternalHandler.handleEdit(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=BoxLiveMonitoringServiceHandler,
    )
