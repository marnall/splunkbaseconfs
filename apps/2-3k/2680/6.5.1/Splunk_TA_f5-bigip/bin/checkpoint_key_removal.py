##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
import import_declare_test  # noqa: F401 isort: skip

import json
import os
import sys

import splunk.rest as rest
import splunk_ta_f5_utility as common_utility
from import_declare_test import ta_name
from solnlib import log

sys.path.insert(
    0, os.path.abspath(os.path.join(__file__, "..", "modinputs", "icontrol"))
)

from checkpoint import Checkpointer  # noqa: E402

logger = log.Logs().get_logger("splunk_ta_checkpoint_key_removal")


class CheckpointKeyRemove:
    """
    This class is used to remove the data_collection_state key from the checkpoint
    """

    def get_inputs(self, session_key):
        inputs_list = []
        try:
            _, response_content = rest.simpleRequest(
                "/servicesNS/nobody/" + str(ta_name) + "/configs/conf-inputs/",
                sessionKey=session_key,
                getargs={"output_mode": "json"},
                raiseAllErrors=True,
            )
            res = json.loads(response_content)
            if res.get("entry"):
                for inputs in res.get("entry"):
                    if inputs.get("name") and "f5_task://" in inputs["name"]:
                        task_name = (inputs["name"]).replace("f5_task://", "")
                        inputs_list.append(task_name)
        except Exception as e:
            logger.error("Exception occured while gettings inputs list: {}".format(e))

        return inputs_list

    def data_collection_state_remove(self):
        session_key = common_utility.get_session_key(logger)
        inputs_list = self.get_inputs(session_key)
        if inputs_list:
            # Remove data_collection_state key for each of the checkpoint
            for input_name in inputs_list:
                checkpoint_object = Checkpointer(session_key, {}, logger)
                checkpoint_object.get_checkpoint_value(input_name)
                logger.info(
                    "Checkpoint value for input {} is: {}".format(
                        input_name, checkpoint_object.checkpoint_value
                    )
                )
                if checkpoint_object.checkpoint_value:
                    checkpoint_value = checkpoint_object.checkpoint_value
                    if checkpoint_value.get("data_collection_state"):
                        logger.info(
                            "Removing the data_collection_state key from the checkpoint for input {}.".format(
                                input_name
                            )
                        )
                        checkpoint_object.remove_key("data_collection_state")
                        try:
                            encode_value = common_utility.encode(
                                json.dumps(checkpoint_object.checkpoint_value)
                            )
                            common_utility.checkpoint_handler(
                                session_key, input_name, str(encode_value), logger
                            )
                            logger.info(
                                "Key data_collection_state removed from the checkpoint for input {}".format(
                                    input_name
                                )
                            )
                        except Exception as e:
                            logger.error(
                                "Error while updating checkpoint after removing the data_collection_state key: {}".format(  # noqa: E501
                                    e
                                )
                            )


if __name__ == "__main__":
    checkpoint_key_remove = CheckpointKeyRemove()
    checkpoint_key_remove.data_collection_state_remove()
