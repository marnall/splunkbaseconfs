#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test  # isort: skip # noqa F401

import os
import traceback

import box_utility
import log_files
import splunk.admin as admin
from solnlib import conf_manager, log

_LOGGER = log.Logs().get_logger(log_files.ta_box_live_monitoring_input_ckpt)


class CheckpointHandler(admin.MConfigHandler):
    def __init__(self, *args, **kwargs):
        admin.MConfigHandler.__init__(self, *args, **kwargs)
        cfm = conf_manager.ConfManager(
            self.getSessionKey(),
            "Splunk_TA_box",
            realm="__REST_CREDENTIAL__#Splunk_TA_box#configs/conf-splunk_ta_box_settings",
        )
        logging = cfm.get_conf("splunk_ta_box_settings").get("logging")
        _LOGGER.setLevel(logging.get("loglevel", "INFO"))

    def setup(self):
        self.supportedArgs.addReqArg("input_name")

    def handleList(self, confInfo):
        """
        This handler is to get checkpoint of data input
        It takes 'input_name' as caller args and
        Returns the confInfo dict object in response.
        """
        try:
            _LOGGER.debug(
                "In checkpoint handler to get checkpoint of live monitoring data input"
            )
            # Get args parameters from the request
            input_name = self.callerArgs.data["input_name"][0]
            checkpoint_dir = os.path.join(
                os.path.normpath(os.environ["SPLUNK_HOME"]),
                "var",
                "lib",
                "splunk",
                "modinputs",
                "box_live_monitoring_service",
            )
            use_state_store = False
            session_key = self.getSessionKey()
            collection_name = import_declare_test.LIVE_MONITORING_EVENTS_CHECKPOINTER
            checkpoint_exist = box_utility.check_if_checkpoint_exist(
                input_name,
                use_state_store,
                session_key,
                checkpoint_dir,
                collection_name,
                _LOGGER,
            )
            if checkpoint_exist:
                _LOGGER.info(
                    "Found checkpoint for live monitoring input {}".format(input_name)
                )
                confInfo["token"]["checkpoint_exist"] = True
            else:
                _LOGGER.info(
                    "Checkpoint not found of file ingestion input {}".format(input_name)
                )
                confInfo["token"]["checkpoint_exist"] = False

        except Exception:
            _LOGGER.error(
                "Error occured while fetching checkpoint for live monitoring input{}: {}".format(
                    input_name, traceback.format_exc()
                )
            )


if __name__ == "__main__":
    admin.init(CheckpointHandler, admin.CONTEXT_APP_AND_USER)
