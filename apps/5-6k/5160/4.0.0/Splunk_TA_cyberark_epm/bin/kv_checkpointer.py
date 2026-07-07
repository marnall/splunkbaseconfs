#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from solnlib.modular_input import checkpointer
from constants import APP_NAME


class Checkpointer:
    def __init__(self, collection_name, session_key):
        self.collection = checkpointer.KVStoreCheckpointer(
            collection_name, session_key, APP_NAME
        )

    def update(self, checkpoint_name, data):
        self.collection.update(checkpoint_name, data)

    def get(self, checkpoint_name):
        return self.collection.get(checkpoint_name)
