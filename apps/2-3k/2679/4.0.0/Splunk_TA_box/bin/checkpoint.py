#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test

import logging
import os
import os.path as op
import json

from solnlib.modular_input import checkpointer, FileCheckpointer

APP_NAME = import_declare_test.ta_name


class Checkpointer:
    def __init__(self, session_key, input_name, collection_name, logger):
        self.session_key = session_key
        self.input_name = input_name
        self.collection_name = collection_name
        self.logger = logger

    def check_for_kv_checkpoint(self):
        try:
            checkpoint_object = checkpointer.KVStoreCheckpointer(
                self.collection_name, self.session_key, APP_NAME
            )
            checkpoint_value = checkpoint_object.get(self.input_name)
            if checkpoint_value:
                return True, checkpoint_value
        except Exception as e:
            self.logger.error(
                "Error occured while getting the KV checkpoint value for the input: {}:{}".format(
                    self.input_name, e
                )
            )
            raise e

        return False, {}

    def check_for_file_checkpoint(self, use_state_store, checkpoint_dir):
        if use_state_store:
            fname = op.join(checkpoint_dir, self.input_name)
            try:
                if op.exists(fname):
                    with open(fname) as f:
                        checkpoint_value = json.load(f)
                    if checkpoint_value:
                        return True, checkpoint_value
            except Exception as e:
                self.logger.error(
                    "Error occured while getting file checkpoint for the input: {}:{}".format(
                        self.input_name, e
                    )
                )
                raise e

            return False, {}
        else:
            try:
                checkpointer_object = checkpointer.FileCheckpointer(checkpoint_dir)
                checkpoint_value = checkpointer_object.get(self.input_name)
                if checkpoint_value:
                    return True, checkpoint_value
            except Exception as e:
                self.logger.error(
                    "Error occured while getting file checkpoint for the input: {}:{}".format(
                        self.input_name, e
                    )
                )
                raise e

            return False, {}

    def get_kv_checkpoint_value(self):
        try:
            checkpoint_object = checkpointer.KVStoreCheckpointer(
                self.collection_name, self.session_key, APP_NAME
            )
            checkpoint_value = checkpoint_object.get(self.input_name)
            return checkpoint_value
        except Exception as e:
            self.logger.error(
                "Error occured while getting the value of checkpoint for the input: {}:{}".format(
                    self.input_name, e
                )
            )
            raise e

    def delete_file_checkpoint(self, use_state_store, checkpoint_dir):
        if use_state_store:
            try:
                fname = op.join(checkpoint_dir, self.input_name)
                if op.exists(fname):
                    os.remove(fname)
            except Exception as e:
                self.logger.error(
                    "Error occured while deleting the file checkpoint for the input: {}:{}".format(
                        self.input_name, e
                    )
                )
                raise e
        else:
            try:
                checkpoint_object = checkpointer.FileCheckpointer(checkpoint_dir)
                checkpoint_object.delete(self.input_name)
            except Exception as e:
                self.logger.error(
                    "Error occured while deleting the file checkpoint for the input: {}:{}".format(
                        self.input_name, e
                    )
                )
                raise e

    def delete_kv_checkpoint(self):
        try:
            checkpoint_object = checkpointer.KVStoreCheckpointer(
                self.collection_name, self.session_key, APP_NAME
            )
            checkpoint_object.delete(self.input_name)
        except Exception as e:
            self.logger.error(
                "Error occured while deleting the KV Store checkpoint for the input: {}:{}".format(
                    self.input_name, e
                )
            )
            raise e

    def update_kv_checkpoint(self, checkpoint_value):
        try:
            checkpoint_object = checkpointer.KVStoreCheckpointer(
                self.collection_name, self.session_key, APP_NAME
            )
            checkpoint_object.update(self.input_name, checkpoint_value)
        except Exception as e:
            self.logger.error(
                "Error occured while updating the kv checkpoint for the input: {}:{}".format(
                    self.input_name, e
                )
            )
            raise e

    def update_file_checkpoint(self, checkpoint_value, checkpoint_dir):
        try:
            fname = op.join(checkpoint_dir, self.input_name)
            with open(fname, "w") as f:
                json.dump(checkpoint_value, f)
        except Exception as e:
            self.logger.error(
                "Error occured while updating the file checkpoint for the input: {}:{}".format(
                    self.input_name, e
                )
            )
            raise e
