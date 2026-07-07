#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test  # isort: skip # noqa: F401
import os
import shutil
import traceback
from typing import Any, Optional, Dict

import sfdc_consts as sc
import sfdc_utility as su
from solnlib.modular_input import FileCheckpointer, checkpointer
from solnlib.splunkenv import make_splunkhome_path
from solnlib import log


class SFDCFileCheckpointer(FileCheckpointer):
    def encode_key(self, key: str) -> str:
        """Override the original 'encode_key' function to handle hash value of checkpoint file name

        :param key: Checkpoint file name in hash
        :return:    Provided 'key' arg in function
        """
        return key


class CheckpointHandler:
    def __init__(self, collection_name: str, sfdc_util_ob: su.SFDCUtil) -> None:
        self.sfdc_util_ob = sfdc_util_ob
        self.kvstore_checkpointer = checkpointer.KVStoreCheckpointer(
            collection_name, sfdc_util_ob.session_key, sc.APP_NAME
        )

    def is_checkpoint_migrated_to_kv(self) -> bool:
        """Funtion to check if the checkpoint for current input has been migrated to KV

        Returns:
            bool: True, in cases, - If KV store checkpoint exist for input
                                  - If KV store checkpoint and file checkpoint does not exist for input
                                  - If file checkpoint does not exist for input

                  False, in case,  - file checkpoint exist and KV store checkpoint does not exist for input
        """
        try:
            file_checkpoint_handler = self.get_file_checkpoint_manager()
            file_checkpoint_exist = self.get_file_checkpoint(file_checkpoint_handler)
            kv_checkpoint_exist = self.get_kv_checkpoint()
            if file_checkpoint_exist and not kv_checkpoint_exist:
                self.sfdc_util_ob.logger.info(
                    "Checkpoint is not migrated from file to kv for input {}".format(
                        self.sfdc_util_ob.input_items["name"]
                    )
                )
                return False

        except Exception as e:
            log.log_exception(
                self.sfdc_util_ob.logger,
                e,
                "Checkpoint migration Error",
                msg_before=f"Some error occurred while checking if checkpoint is migrated from file to kv for input {self.sfdc_util_ob.input_items['name']}.\nTraceback = {traceback.format_exc()}",
            )
            raise e
        return True

    def migrate_file_to_kv_checkpoint(self) -> bool:
        """Function to migrate existing file checkpoint to KV checkpoint if there is no existing KV checkpoint
           and there exist file checkpoint to migrate

        :return: True, in cases, - If KV store checkpoint exist for input
                                 - If KV store checkpoint and file checkpoint does not exist for input
                                 - Migration of file to KV store checkpoint completes successfully when
                                   file checkpoint exist and KV store checkpoint does not exist for input

                 False, in case,  - Migration of file to KV store checkpoint completes unsuccessfully when
                                    file checkpoint exist and KV store checkpoint does not exist for input
        """
        try:
            file_checkpoint_handler = self.get_file_checkpoint_manager()
            file_checkpoint_value = self.get_file_checkpoint(file_checkpoint_handler)
            if not file_checkpoint_value:
                return True
            self.sfdc_util_ob.logger.info(
                f"Proceeding to migrate file to kv checkpoint for input '{self.sfdc_util_ob.input_items['name']}'"
            )
            del file_checkpoint_value["namespaces"]
            self.update_kv_checkpoint(file_checkpoint_value)
            self.sfdc_util_ob.logger.info(
                f"Successfully updated the KV store checkpoint for input '{self.sfdc_util_ob.input_items['name']}'"
            )
            self.delete_file_checkpoint()
            self.sfdc_util_ob.logger.info(
                f"Successfully deleted the file checkpoint for input '{self.sfdc_util_ob.input_items['name']}'"
            )

            self.sfdc_util_ob.logger.info(
                "Checkpoint migrated successfully from file to kv for "
                f"input '{self.sfdc_util_ob.input_items['name']}' with value '{file_checkpoint_value}'"
            )
            return True

        except Exception as e:
            log.log_exception(
                self.sfdc_util_ob.logger,
                e,
                "File checkpoint migration Error",
                msg_before=f"Some error occurred while migrating file to kv checkpoint for input {self.sfdc_util_ob.input_items['name']}.\nTraceback = {traceback.format_exc()}",
            )
        return False

    def get_kv_checkpoint(self) -> Optional[Dict]:
        """Function to get the KV checkpoint value for the given input

        :return: Document data under `key` or `None` in case of no data.
        :Raises: Exception: When an error occurred in Splunk (not 404 code),
                            can be 503 code, when Splunk is restarting and KV Store is not
                            yet initialized.
        """
        try:
            checkpoint_value = self.kvstore_checkpointer.get(
                self.sfdc_util_ob.input_items["name"]
            )
            return checkpoint_value
        except Exception as e:
            log.log_exception(
                self.sfdc_util_ob.logger,
                e,
                "Get kv checkpoint Error",
                msg_before=f"Error occurred while getting the KV checkpoint value for input {self.sfdc_util_ob.input_items['name']}",
            )
            raise e

    def update_kv_checkpoint(self, checkpoint_value: Any) -> None:
        """Function to update the KV checkpoint value for the given input

        :Raises: Exception: when an error occurred in Splunk, for example,
                            when Splunk is restarting and KV Store is not yet initialized.
        """
        try:
            self.kvstore_checkpointer.update(
                self.sfdc_util_ob.input_items["name"], checkpoint_value
            )
        except Exception as e:
            log.log_exception(
                self.sfdc_util_ob.logger,
                e,
                "Update kv checkpoint Error",
                msg_before=f"Error occurred while updating the KV checkpoint value for input {self.sfdc_util_ob.input_items['name']}",
            )
            raise e

    def delete_kv_checkpoint(self) -> None:
        """Function to delete the KV checkpoint value for the given input

        :Raises: Exception: When an error occurred in Splunk (not 404 code),
                            can be 503 code, when Splunk is restarting and KV Store is not
                            yet initialized.
        """
        try:
            self.kvstore_checkpointer.delete(self.sfdc_util_ob.input_items["name"])
        except Exception as e:
            log.log_exception(
                self.sfdc_util_ob.logger,
                e,
                "Delete kv checkpoint Error",
                msg_before=f"Error occured while deleting the KV checkpoint for input {self.sfdc_util_ob.input_items['name']}",
            )
            raise e

    def get_file_checkpoint_manager(self) -> Optional[SFDCFileCheckpointer]:
        """Function to get the File checkpoint manager

        :return: None, if there is no corresponding checkpoint directory for given input else Filecheckpoint object
        """
        if not self.sfdc_util_ob.file_checkpoint_dir:
            return None

        hashed_folder = su.get_hashed_value(self.sfdc_util_ob.input_items["name"])
        new_file_checkpoint_dir = os.path.join(
            self.sfdc_util_ob.file_checkpoint_dir, hashed_folder
        )
        if not os.path.exists(new_file_checkpoint_dir):
            return None
        file_checkpoint_handler = SFDCFileCheckpointer(new_file_checkpoint_dir)
        return file_checkpoint_handler

    def get_file_checkpoint(
        self, file_checkpoint_handler: Optional[SFDCFileCheckpointer]
    ) -> Optional[Dict[str, Any]]:
        """Function to get the File checkpoint value for the given input

        :param file_checkpoint_handler: Filecheckpoint object
        :return:                        None, if there is no corresponding checkpoint directory for given input
                                        else Dict containing checkpoint value
        """
        file_checkpoint_value = None
        if file_checkpoint_handler:
            file_checkpoint_value = (
                file_checkpoint_handler.get(
                    su.get_hashed_value(self.sfdc_util_ob.input_items["name"])
                )
                or None
            )
        return file_checkpoint_value

    def delete_file_checkpoint(self) -> None:
        """Function to delete the File checkpoint for the given input"""
        hashed_folder = su.get_hashed_value(self.sfdc_util_ob.input_items["name"])
        file_checkpoint_dir = make_splunkhome_path(
            [
                "var",
                "lib",
                "splunk",
                "modinputs",
                self.sfdc_util_ob.input_items["input_type"],
                hashed_folder,
            ]
        )
        # If the directory exists remove checkpoint
        if os.path.exists(file_checkpoint_dir):
            shutil.rmtree(file_checkpoint_dir)
