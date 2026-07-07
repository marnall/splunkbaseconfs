"""Config file."""
# File: vectraxdr_config.py
#
# Copyright (c) 2023-2025 Vectra
#
# This unpublished material is proprietary to Vectra.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Vectra.
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

import json
import os

import encryption_helper
import requests
from dotenv import load_dotenv


# Load '.env' file to the environment variables.
load_dotenv()

CONTENT_TYPE = "application/json"
CONTENT_HTML_TYPE = "text/html"
DEFAULT_ASSET_ID = "10"
DEFAULT_HEADERS = {"Content-Type": CONTENT_TYPE}
STATE_FILE_PATH = f"/opt/phantom/local_data/app_states/fce4056c-6b35-4ecd-a900-896ad72d32fe/{DEFAULT_ASSET_ID}_state.json"
USER_AGENT = "VectraXDR-SplunkSOAR-1.0.0"
DUMMY_BASE_URL = "https://1234567891243.uw2.portal.vectra.ai"
MAIN_MODULE = "vectraxdr_connector.py"
session_id = None

ACTION_HEADER = {"Authorization": "Bearer <dummy_access_token>", "User-agent": USER_AGENT}
TOKEN_HEADER = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json", "User-agent": USER_AGENT}
TOKEN_DATA = {"client_id": "<client_id>", "client_secret": "<dummy_client_secret>", "grant_type": "api_key"}

cipher_text = encryption_helper.encrypt("<dummy_client_secret>", DEFAULT_ASSET_ID)

TEST_JSON = {
    "action": "<action name>",
    "identifier": "<action_id>",
    "asset_id": DEFAULT_ASSET_ID,
    "config": {
        "appname": "-",
        "directory": "vectraxdrsplunksoar_fce4056c-6b35-4ecd-a900-896ad72d32fe",
        "base_url": DUMMY_BASE_URL,
        "client_id": "<client_id>",
        "client_secret": cipher_text,
        "main_module": MAIN_MODULE,
    },
    "main_module": MAIN_MODULE,
    "debug_level": 3,
    "dec_key": DEFAULT_ASSET_ID,
    "parameters": [{}],
}

TOKEN_DUMMY_ACCESS_TOKEN_1 = "dummy value 1"
TOKEN_DUMMY_REFRESH_TOKEN_1 = "dummy value 1"

TOKEN_DUMMY_ACCESS_TOKEN_2 = "dummy value 2"
TOKEN_DUMMY_REFRESH_TOKEN_2 = "dummy value 2"

TOKEN_DUMMY_ACCESS_CIPHER_1 = encryption_helper.encrypt(TOKEN_DUMMY_ACCESS_TOKEN_1, DEFAULT_ASSET_ID)
TOKEN_DUMMY_REFRESH_CIPHER_1 = encryption_helper.encrypt(TOKEN_DUMMY_REFRESH_TOKEN_1, DEFAULT_ASSET_ID)

TOKEN_DUMMY_ACCESS_CIPHER_2 = encryption_helper.encrypt(TOKEN_DUMMY_ACCESS_TOKEN_2, DEFAULT_ASSET_ID)
TOKEN_DUMMY_REFRESH_CIPHER_2 = encryption_helper.encrypt(TOKEN_DUMMY_REFRESH_TOKEN_2, DEFAULT_ASSET_ID)


def set_state_file(Token=False):
    """Save the state file as per requirement.

    :param dmaToken: True if access token is required in the state file
    """
    state_file = {
        "app_version": "1.0.0",
    }
    if Token:
        state_file["token"] = {
            "access_token": encryption_helper.encrypt("<dummy_access_token>", DEFAULT_ASSET_ID),
            "refresh_token": encryption_helper.encrypt("<dummy_refresh_token>", DEFAULT_ASSET_ID),
            "expire": 33333333,
        }
    state_file = json.dumps(state_file)

    with open(STATE_FILE_PATH, "w+") as fp:
        fp.write(state_file)


def get_session_id(connector, verify=False):
    """Generate the session id.

    :param connector: The Connector object
    :param verify: Boolean to check server certificate
    :return: User session token
    """
    global session_id
    if session_id:
        return session_id
    login_url = f"{connector._get_phantom_base_url()}login"

    # Accessing the Login page
    r = requests.get(login_url, verify=verify)
    csrftoken = r.cookies["csrftoken"]

    # TODO: Remove this
    os.environ["USERNAME"] = "soar_local_admin"
    os.environ["PASSWORD"] = "password"  # pragma: allowlist secret  width="300" height="390"
    data = {"username": os.environ.get("USERNAME"), "password": os.environ.get("PASSWORD"), "csrfmiddlewaretoken": csrftoken}

    headers = {"Cookie": f"csrftoken={csrftoken}", "Referer": login_url}

    # Logging into the Platform to get the session id
    r2 = requests.post(login_url, verify=verify, data=data, headers=headers)
    print(r2.text)
    connector._set_csrf_info(csrftoken, headers["Referer"])
    session_id = r2.cookies["sessionid"]
    return r2.cookies["sessionid"]
