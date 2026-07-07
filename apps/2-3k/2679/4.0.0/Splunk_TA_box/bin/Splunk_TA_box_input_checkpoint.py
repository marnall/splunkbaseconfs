#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import import_declare_test  # isort: skip # noqa F401
import traceback

import box_utility
import log_files
import splunk.admin as admin
from solnlib import conf_manager, log
from solnlib.splunkenv import make_splunkhome_path

_LOGGER = log.Logs().get_logger(log_files.ta_box_data_input_ckpt)


class CheckpointHandler(admin.MConfigHandler):
    def __init__(self, *args, **kwargs):
        admin.MConfigHandler.__init__(self, *args, **kwargs)
        cfm = conf_manager.ConfManager(
            self.getSessionKey(),
            "Splunk_TA_box",
            realm="__REST_CREDENTIAL__#Splunk_TA_box#configs/conf-splunk_ta_box_settings",
        )
        logging_config = cfm.get_conf("splunk_ta_box_settings").get("logging")
        _LOGGER.setLevel(logging_config.get("loglevel", "INFO"))

    def setup(self):
        self.supportedArgs.addReqArg("input_name")
        self.supportedArgs.addReqArg("rest_endpoint_value")
        return

    @staticmethod
    def get_session_key(self):
        return self.getSessionKey()

    """
    This handler is to get checkpoint of data input
    It takes 'input_name' as caller args and
    Returns the confInfo dict object in response.
    """

    def handleList(self, confInfo):
        try:
            _LOGGER.debug("In checkpoint handler to get checkpoint of data input")
            # Get args parameters from the request
            input_name = self.callerArgs.data["input_name"][0]
            rest_endpoint_value = self.callerArgs.data["rest_endpoint_value"][0]
            session_key = self.get_session_key(self)
            checkpoint_dir = make_splunkhome_path(
                ["var", "lib", "splunk", "modinputs", "box_service"]
            )
            historical_input_endpoints = ["events"]
            if rest_endpoint_value in historical_input_endpoints:
                use_state_store = True
                collection_name_value = (
                    import_declare_test.COLLECTION_VALUE_FROM_ENDPOINT.get(
                        rest_endpoint_value
                    )
                )
                checkpoint_exist = box_utility.check_if_checkpoint_exist(
                    input_name,
                    use_state_store,
                    session_key,
                    checkpoint_dir,
                    collection_name_value,
                    _LOGGER,
                )
                if checkpoint_exist:
                    _LOGGER.info("Found checkpoint for %s", input_name)
                    confInfo["token"]["checkpoint_exist"] = True
                else:
                    _LOGGER.info("Checkpoint not found for %s", input_name)
                    confInfo["token"]["checkpoint_exist"] = False
            else:
                _LOGGER.info("Checkpoint not found for %s", input_name)
                confInfo["token"]["checkpoint_exist"] = False
        except Exception:
            _LOGGER.error(
                "Error occurred while getting the checkpoint, Error: %s",
                traceback.format_exc(),
            )
        return


if __name__ == "__main__":
    admin.init(CheckpointHandler, admin.CONTEXT_APP_AND_USER)
