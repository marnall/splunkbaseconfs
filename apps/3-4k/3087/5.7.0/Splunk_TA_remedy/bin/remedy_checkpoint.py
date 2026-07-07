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
import splunk_ta_remedy_declare

import os
import traceback
import logging
from solnlib.modular_input import FileCheckpointer, KVStoreCheckpointer
from remedy_consts import APP_NAME
from logger_manager import get_logger


class KVCheckpointHandler:
    """
    All the KVstore Checkpoint related methods are defined in this class.
    """

    def __init__(
        self,
        collection_name: str,
        session_key: str,
        kv_checkpoint_key_name: str,
        _LOGGER=get_logger("input"),
    ) -> None:
        self.kvstore_checkpointer = KVStoreCheckpointer(
            collection_name=collection_name, session_key=session_key, app=APP_NAME
        )
        self.kv_checkpoint_key_name = kv_checkpoint_key_name
        self.input_name = kv_checkpoint_key_name.split(".")[0]
        self.file_checkpointer = FileCheckpointer(
            os.path.join(
                os.path.normpath(os.environ["SPLUNK_HOME"]),
                "var",
                "lib",
                "splunk",
                "modinputs",
                "remedy_input",
            )
        )
        self._LOGGER = _LOGGER

    def get_kv_checkpoint(self) -> dict:
        try:
            kvstore_ckpt_data = self.kvstore_checkpointer.get(
                self.kv_checkpoint_key_name
            )
            if kvstore_ckpt_data:
                self._LOGGER.debug(
                    f"KV store Ckpt for input: {self.input_name} fetched successfully. Data: {kvstore_ckpt_data}"
                )
                return kvstore_ckpt_data
            else:
                self._LOGGER.debug(
                    f"KV store Ckpt for input: {self.input_name} doesn't exist."
                )
        except Exception as exc:
            self._LOGGER.error(
                f"Exception Occured while fetching KV Checkpoint for input: {self.input_name}\nTraceback={traceback.format_exc()}"
            )
            raise exc

    def update_kv_checkpoint(self, checkpoint_data):
        try:
            self.kvstore_checkpointer.update(
                self.kv_checkpoint_key_name, checkpoint_data
            )
            self._LOGGER.debug(
                f"Successfully updated KV Ckpt for input: {self.input_name} to {checkpoint_data}"
            )
        except Exception as exc:
            self._LOGGER.error(
                f"Exception Occured while updation of KV ckpt for input {self.input_name} to {checkpoint_data}\nTraceback={traceback.format_exc()}"
            )
            raise exc

    def delete_kv_checkpoint(self):
        try:
            if self.get_kv_checkpoint():
                self.kvstore_checkpointer.delete(self.kv_checkpoint_key_name)
                self._LOGGER.debug(
                    f"Successfully deleted KV Ckpt for input: {self.input_name}"
                )
            else:
                self._LOGGER.debug(
                    f"KVStore checkpoint for input: {self.input_name} doesn't exist"
                )
        except Exception as exc:
            self._LOGGER.error(
                f"Exception Occured while deletion of KV Ckpt for input: {self.input_name}\nTraceback={traceback.format_exc()}"
            )
            raise exc

    def get_file_checkpoint(self) -> dict:
        try:
            file_ckpt_data = self.file_checkpointer.get(self.input_name)
            if file_ckpt_data:
                self._LOGGER.debug(
                    f"File Ckpt for input: {self.input_name} fetched successfully. Data: {file_ckpt_data}"
                )
                return file_ckpt_data
            else:
                self._LOGGER.debug(
                    f"File checkpoint for input: {self.input_name} not found."
                )
        except Exception as exc:
            self._LOGGER.error(
                f"Exception Occured while fetching File Checkpoint for input: {self.input_name}\nTraceback={traceback.format_exc()}"
            )
            raise exc

    def migrate_file_ckpt_to_kvstore(self) -> bool:
        try:
            file_ckpt_data = self.get_file_checkpoint()
            if not file_ckpt_data:
                return True
            self.update_kv_checkpoint(file_ckpt_data)
            self.file_checkpointer.delete(self.input_name)
            self._LOGGER.info(
                f"Checkpoint for input {self.input_name} has been successfully migrated from File to KVStore"
            )
            return True
        except Exception as exc:
            self._LOGGER.error(
                f"Exception occured while file to KV ckpt migration for input: {self.input_name}\nTraceback={traceback.format_exc()}"
            )
            raise exc
