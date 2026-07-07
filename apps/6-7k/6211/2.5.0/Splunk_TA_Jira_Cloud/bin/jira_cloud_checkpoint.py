#
# SPDX-FileCopyrightText: 2025 Splunk LLC.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import os.path
import traceback
import sys

from solnlib.modular_input import checkpointer
import jira_cloud_utils as utils
import jira_cloud_consts as jcc

APP_NAME = __file__.split(os.path.sep)[-3]


class Checkpoint:
    def _get_checkpointer(self):
        try:
            kv_checkpointer = checkpointer.KVStoreCheckpointer(
                self._checkpoint_name, self._session_key, APP_NAME
            )
            return kv_checkpointer
        except Exception as e:
            msg = "Error in Checkpoint handling: {}".format(traceback.format_exc())
            utils.add_ucc_error_logger(
                logger=self._logger,
                logger_type=jcc.GENERAL_EXCEPTION,
                exception=e,
                exc_label=self.exc_label,
                msg_before=msg,
            )
            sys.exit(1)

    def __init__(self, *, logger, input_name, session_key) -> None:
        self._logger = logger
        self._session_key = session_key
        self._checkpoint_name = input_name.replace("://", "_")
        self.exc_label = jcc.UCC_EXCEPTION_EXE_LABEL.format("jira_cloud_checkpoint")
        self._checkpointer = self._get_checkpointer()

    def get(self, *, parameter):
        if not self._checkpointer:
            return None
        checkpoint_data = self._checkpointer.get(self._checkpoint_name)
        if not checkpoint_data:
            self._logger.info(
                "No checkpoint found for {}".format(self._checkpoint_name)
            )
            return None
        value = checkpoint_data.get(parameter)
        self._logger.debug(
            "Get checkpoint for {}; parameter: {}, value: {}".format(
                self._checkpoint_name, parameter, value
            )
        )
        return value

    def update(self, *, parameter, value):
        checkpoint_data = {parameter: value}
        self._checkpointer.update(self._checkpoint_name, checkpoint_data)
        self._logger.debug(
            "Updated checkpoint for {}; parameter: {}, new value: {}".format(
                self._checkpoint_name, parameter, value
            )
        )

    def get_checkpoint(self, checkpoint_name):
        try:
            checkpoint_data = self._checkpointer.get(checkpoint_name)
            if not checkpoint_data:
                self._logger.info(
                    "No checkpoint found for the input: {}".format(checkpoint_name)
                )
                return None

            self._logger.info(
                "Found checkpoint for {} : {}".format(checkpoint_name, checkpoint_data)
            )
            return checkpoint_data
        except Exception as e:
            msg = "Error while fetching the checkpoint information. Reason: {}".format(
                traceback.format_exc()
            )
            utils.add_ucc_error_logger(
                logger=self._logger,
                logger_type=jcc.GENERAL_EXCEPTION,
                exception=e,
                exc_label=self.exc_label,
                msg_before=msg,
            )
            sys.exit(1)

    def update_checkpoint(self, checkpoint_name, checkpoint_data):
        try:
            self._checkpointer.update(checkpoint_name, checkpoint_data)
            self._logger.debug(
                "Updated the checkpoint data in UTC timezone: {}".format(
                    checkpoint_data
                )
            )
        except Exception as e:
            msg = "Error while updating the checkpoint information. Reason: {}".format(
                traceback.format_exc()
            )
            utils.add_ucc_error_logger(
                logger=self._logger,
                logger_type=jcc.GENERAL_EXCEPTION,
                exception=e,
                exc_label=self.exc_label,
                msg_before=msg,
            )
            sys.exit(1)

    def delete_checkpoint(self, checkpoint_name):
        try:
            self._checkpointer.delete(checkpoint_name)
            self._logger.info(
                "Successfully deleted the KV checkpoint for input = {}".format(
                    checkpoint_name
                )
            )
        except Exception as e:
            msg = "Error while deleting the checkpoint. Reason: {}".format(
                traceback.format_exc()
            )
            utils.add_ucc_error_logger(
                logger=self._logger,
                logger_type=jcc.GENERAL_EXCEPTION,
                exception=e,
                exc_label=self.exc_label,
                msg_before=msg,
            )
            sys.exit(1)


class JiraCloudCheckpoint(Checkpoint):
    _START_TIME = "start_time"

    def __init__(self, *, logger, input_name, session_key) -> None:
        super().__init__(logger=logger, input_name=input_name, session_key=session_key)

    def get_start_time(self):
        return self.get(parameter=self._START_TIME)

    def update_start_time(self, value):
        return self.update(parameter=self._START_TIME, value=value)

    def get_checkpoint_data(self, checkpoint_name):
        return self.get_checkpoint(checkpoint_name)

    def update_checkpoint_data(self, checkpoint_name, checkpoint_data):
        return self.update_checkpoint(checkpoint_name, checkpoint_data)
