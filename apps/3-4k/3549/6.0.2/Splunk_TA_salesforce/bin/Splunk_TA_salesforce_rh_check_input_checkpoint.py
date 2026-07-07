#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""
This module will be used to validate that if the checkpoint exist for given input or not

This file contains certain ignores for certain linters.

* isort ignores:
- isort: skip = Particular import must be the first import.

* flake8 ignores:
- noqa: F401 -> Def = module imported but unused
    Reason for ignoring = This is necessary as it contains adding a path to sys.path
"""
from typing import Dict, Any

import import_declare_test  # isort: skip # noqa: F401
import os
import traceback

import sfdc_checkpoint
import sfdc_consts as sc
import sfdc_utility as su
import splunk.admin as admin
from solnlib import log

"""
REST Endpoint to validate the if the checkpoint exist for given input or not
"""


class CheckpointHandler(admin.MConfigHandler):

    """
    This method checks which action is getting called and what parameters are required for the request.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.sfdc_util_ob = su.SFDCUtil(
            log_file="splunk_ta_salesforce_rh_check_input_checkpoint",
            session_key=self.getSessionKey(),
        )

    def setup(self):
        if self.requestedAction == admin.ACTION_LIST:
            # Add required args in supported args
            self.supportedArgs.addReqArg("input_name")
            self.supportedArgs.addReqArg("service_name")
        return

    """
    This handler is to validate the checkpoint exist for given input or not
    It takes 'input_name' as caller args and
    Returns the confInfo dict object in response.
    """

    def handleList(self, confInfo: Dict[str, Any]) -> None:
        # Get args parameters from the request
        try:
            self.sfdc_util_ob.input_items["name"] = self.callerArgs.data["input_name"][
                0
            ]
            splunk_home = os.path.normpath(os.environ["SPLUNK_HOME"])
            service_name = self.callerArgs.data["service_name"][0]
            self.sfdc_util_ob.file_checkpoint_dir = os.path.join(
                splunk_home,
                "var",
                "lib",
                "splunk",
                "modinputs",
                service_name,
            )
            self.sfdc_util_ob.logger.info(
                f"Entering handler to check checkpoint for input {self.sfdc_util_ob.input_items['name']}"
            )
            checkpoint_collection_name = sc.SFDC_OBJECT_CHECKPOINT_COLLECTION_NAME
            if service_name == "sfdc_event_log":
                checkpoint_collection_name = sc.SFDC_EVENTLOG_CHECKPOINT_COLLECTION_NAME
            checkpoint_handler = sfdc_checkpoint.CheckpointHandler(
                checkpoint_collection_name, self.sfdc_util_ob
            )
            confInfo["token"]["checkpoint_exist"] = False
            if checkpoint_handler.get_kv_checkpoint():
                confInfo["token"]["checkpoint_exist"] = True
            else:
                file_checkpoint_handler = (
                    checkpoint_handler.get_file_checkpoint_manager()
                )
                file_checkpoint_value = checkpoint_handler.get_file_checkpoint(
                    file_checkpoint_handler
                )
                if file_checkpoint_value:
                    confInfo["token"]["checkpoint_exist"] = True
            if confInfo["token"]["checkpoint_exist"]:
                self.sfdc_util_ob.logger.info(
                    f"Found checkpoint for input '{self.sfdc_util_ob.input_items['name']}'"
                )
            else:
                self.sfdc_util_ob.logger.info(
                    f"Checkpoint not found for input '{self.sfdc_util_ob.input_items['name']}'"
                )

        except Exception as e:
            log.log_exception(
                self.sfdc_util_ob.logger,
                e,
                "Checkpoint handleList Error",
                msg_before=(
                    f"Error occured while fetching checkpoint for input '{self.sfdc_util_ob.input_items['name']}'.\nTraceback: {traceback.format_exc()}"
                ),
            )


if __name__ == "__main__":
    admin.init(CheckpointHandler, admin.CONTEXT_APP_AND_USER)
