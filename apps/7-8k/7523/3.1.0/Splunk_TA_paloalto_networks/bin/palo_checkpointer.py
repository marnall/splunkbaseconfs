#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import os.path
import traceback
import logging
from typing import Optional, Union

from solnlib.modular_input import checkpointer
from solnlib import log

APP_NAME = __file__.split(os.path.sep)[-3]


class Checkpoint:
    def _get_checkpointer(self) -> Optional[checkpointer.KVStoreCheckpointer]:
        """
        Creates KVstore checkpoint for modular input

        :returns: KVStoreCheckpointer instance if created successfully
        """
        try:
            kv_checkpointer = checkpointer.KVStoreCheckpointer(
                self._checkpoint_name, self._session_key, APP_NAME
            )
            self._logger.debug(
                f"Checkpoint successfully created for {self._checkpoint_name, self._session_key, APP_NAME,}"
            )
            return kv_checkpointer
        except Exception as e:
            log.log_exception(
                self._logger,
                e,
                "Checkpointer Error (KVstore)",
                msg_before=f"Error in Checkpoint handling: {traceback.format_exc()}",
            )
            return None

    def __init__(
        self, logger: logging.Logger, input_name: str, session_key: str
    ) -> None:
        self._logger = logger
        self._session_key = session_key
        self._checkpoint_name = input_name.replace("://", "_")
        self._checkpointer = self._get_checkpointer()

    def get(self, parameter: str) -> Optional[Union[str, int]]:
        """
        Gets data from checkpoint by requested parameter if exists.

        :param parameter: key of the document to get.
        :returns: value for requested key if exists.
        """
        if not self._checkpointer:
            return None
        value = self._checkpointer.get(parameter)
        if not value:
            self._logger.info(
                f"No data for checkpoint {self._checkpoint_name} with parameter: {parameter}"
            )
            return None
        self._logger.info(
            f"Get checkpoint for {self._checkpoint_name}; parameter: {parameter}, value: {value}"
        )
        return value

    def delete(self, parameter: str) -> None:
        """
        Deletes data from checkpoint by requested parameter.

        :param parameter: key of the document to delete.
        """
        self._checkpointer.delete(parameter)
        self._logger.info(
            f"Deleted parameter {parameter} for {self._checkpoint_name} checkpoint;"
        )

    def update(self, parameter: str, value: Union[str, int]) -> None:
        """
        Updates data in checkpoint by key-value pair.

        :param parameter: key of the document to update.
        :param value: value of the document to update.
        """
        self._checkpointer.update(parameter, value)
        self._logger.info(
            f"Updated checkpoint for {self._checkpoint_name}; parameter: {parameter}, new value: {value}"
        )
