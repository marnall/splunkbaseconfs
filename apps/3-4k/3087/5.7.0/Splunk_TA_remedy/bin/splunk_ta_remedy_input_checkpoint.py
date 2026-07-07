#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""

* isort ignores:
- isort: skip = Should not be sorted.
* flake8 ignores:
- noqa: F401 -> Def = module imported but unused
    Reason for ignoring = This is necessary as it contains adding a path to sys.path
"""

import splunk_ta_remedy_declare  # isort: skip # noqa: F401
import traceback

import splunk.admin as admin
from logger_manager import get_logger
from remedy_consts import CHECKPOINT_COLLECTION_NAME, APP_NAME
from remedy_checkpoint import KVCheckpointHandler

_LOGGER = get_logger("data_input_checkpoint")


class CheckpointHandler(admin.MConfigHandler):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.session_key = self.getSessionKey()

    def setup(self):
        self.supportedArgs.addReqArg("input_name")
        return

    """
    This handler is to get checkpoint of data input
    It takes 'input_name' as caller args and
    Returns the confInfo dict object in response.
    """

    def handleList(self, confInfo):
        try:
            _LOGGER.debug("In checkpoint handler to get checkpoint of data input")
            # # Get args parameters from the request
            _LOGGER.info("self.callerArgs.data: {}".format(self.callerArgs.data))
            kv_checkpoint_key_name = self.callerArgs.data["input_name"][0]
            checkpoint_data = {}
            ckpt_manager = KVCheckpointHandler(
                CHECKPOINT_COLLECTION_NAME,
                self.session_key,
                kv_checkpoint_key_name,
                _LOGGER,
            )
            checkpoint_data = ckpt_manager.get_kv_checkpoint()
            if not checkpoint_data:
                checkpoint_data = ckpt_manager.get_file_checkpoint()

            if checkpoint_data:
                _LOGGER.info("Found checkpoint for {}".format(kv_checkpoint_key_name))
                confInfo["token"]["checkpoint_exist"] = True
            else:
                _LOGGER.info(
                    "Checkpoint not found for {}".format(kv_checkpoint_key_name)
                )
                confInfo["token"]["checkpoint_exist"] = False

        except Exception:
            _LOGGER.error(
                "Error occured while fetching checkpoint for input{}: {}".format(
                    kv_checkpoint_key_name, traceback.format_exc()
                )
            )
        return


if __name__ == "__main__":
    admin.init(CheckpointHandler, admin.CONTEXT_APP_AND_USER)
