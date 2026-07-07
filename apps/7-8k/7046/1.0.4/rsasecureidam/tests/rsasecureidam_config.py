# File: rsasecureidam_config.py
#
# Copyright (c) 2023-2025 Splunk Inc.
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

DEFAULT_ASSET_ID = "20000"
TEST_JSON = {
    "action": "<action name>",
    "identifier": "<action_name>",
    "asset_id": DEFAULT_ASSET_ID,
    "config": {
        "appname": "-",
        "directory": "rsasecureid-2134d245-43c5-473a-a86f-53fa598bb28d",
        "main_module": "rsasecureidam_connector.py",
        "url": "https://base_url",
        "username": "username",
        "password": "password",  # pragma: allowlist secret
        "super_admin_user": "super_admin_user",
        "super_admin_user_password": "super_admin_user_password",  # pragma: allowlist secret
    },
    "debug_level": 3,
    "dec_key": DEFAULT_ASSET_ID,
    "parameters": [{}],
}
