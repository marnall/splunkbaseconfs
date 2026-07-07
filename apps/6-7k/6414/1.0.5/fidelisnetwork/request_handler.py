# File: request_handler.py
#
# Copyright (c) 2022-2025 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#
#
import json
import os

import encryption_helper


class RequestStateHandler:
    def __init__(self, asset_id):
        asset_id = str(asset_id)
        if asset_id and asset_id.isalnum():
            self._asset_id = asset_id
        else:
            raise AttributeError("RequestStateHandler got invalid asset_id")

    def _encrypt_state(self, state):
        if "x_uid" in state:
            oauth_token = state["x_uid"]
            state["x_uid"] = encryption_helper.encrypt(  # pylint: disable=E1101
                json.dumps(oauth_token), self._asset_id
            )
        return state

    def _decrypt_state(self, state):
        if "x_uid" in state:
            oauth_token = encryption_helper.decrypt(  # pylint: disable=E1101
                state["x_uid"], self._asset_id
            )
            state["x_uid"] = json.loads(oauth_token)
        return state

    def _get_state_file(self):
        dirpath = os.path.split(__file__)[0]
        state_file = f"{dirpath}/{self._asset_id}_state.json"
        return state_file

    def delete_state(self):
        state_file = self._get_state_file()
        try:
            os.remove(state_file)
        except Exception:
            pass

        return True

    def save_state(self, state):
        state = self._encrypt_state(state)
        state_file = self._get_state_file()
        try:
            with open(state_file, "w+") as fp:
                fp.write(json.dumps(state))
        except Exception:
            pass

        return True

    def load_state(self):
        state_file = self._get_state_file()
        state = {}
        try:
            with open(state_file) as fp:
                in_json = fp.read()
                state = json.loads(in_json)
        except Exception:
            pass

        state = self._decrypt_state(state)
        return state
