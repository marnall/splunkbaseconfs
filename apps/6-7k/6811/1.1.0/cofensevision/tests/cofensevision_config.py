# File: config.py
#
# Copyright (c) 2023-2026 Cofense
#
# This unpublished material is proprietary to Cofense.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Cofense.
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
import uuid

import encryption_helper
import requests
from dotenv import load_dotenv


# Load '.env' file to the environment variables.
load_dotenv()

CONTENT_TYPE = "application/json"
DEFAULT_ASSET_ID = "20000"
DEFAULT_HEADERS = {"Content-Type": CONTENT_TYPE}
STATE_FILE_PATH = f"/opt/phantom/local_data/app_states/9a810074-0261-4c91-99d4-7ed782ee12a8/{DEFAULT_ASSET_ID}_state.json"
CLIENT_ID = "<client_id>"
ACTION_HEADER = {"Accept": CONTENT_TYPE, "Content-Type": CONTENT_TYPE, "Authorization": "Bearer <dummy_token>"}
STREAM_ACTION_HEADER = {"Content-Type": CONTENT_TYPE, "Authorization": "Bearer <dummy_token>"}
TOKEN_HEADER = {"Content-Type": "application/x-www-form-urlencoded"}
TOKEN_DATA = {"client_id": CLIENT_ID, "client_secret": "<dummy_client_secret>", "grant_type": "client_credentials"}

cipher_text = encryption_helper.encrypt("<dummy_client_secret>", DEFAULT_ASSET_ID)

TEST_JSON = {
    "action": "<action name>",
    "identifier": "<action_id>",
    "asset_id": DEFAULT_ASSET_ID,
    "config": {
        "appname": "-",
        "directory": "cofensevision-9a810074-0261-4c91-99d4-7ed782ee12a8",
        "base_url": "https://base_url",
        "client_id": CLIENT_ID,
        "client_secret": cipher_text,
        "main_module": "cofensevision_connector.py",
    },
    "debug_level": 0,
    "dec_key": DEFAULT_ASSET_ID,
    "parameters": [{}],
}

TOKEN_DUMMY_TEXT_1 = "dummy value 1"
TOKEN_DUMMY_TEXT_2 = "dummy value 2"
TOKEN_DUMMY_CIPHER_1 = encryption_helper.encrypt(TOKEN_DUMMY_TEXT_1, DEFAULT_ASSET_ID)
TOKEN_DUMMY_CIPHER_2 = encryption_helper.encrypt(TOKEN_DUMMY_TEXT_2, DEFAULT_ASSET_ID)


def set_state_file(client_id=False, access_token=False, raw=None):
    """Save the state file as per requirement.

    :param client_id: True if client id is required in the state file
    :param access_token: True if access token is required in the state file
    :param raw: Raw content to save the state file
    """
    if raw and isinstance(raw, str):
        state_file = raw
    else:
        state_file = {
            "app_version": "1.0.0",
        }
        if client_id:
            state_file["client_id"] = CLIENT_ID
        if access_token:
            state_file["token"] = {"access_token": encryption_helper.encrypt("<dummy_token>", DEFAULT_ASSET_ID)}
        state_file = json.dumps(state_file)

    with open(STATE_FILE_PATH, "w+") as fp:
        fp.write(state_file)


def get_session_id(connector, verify=False):
    """Generate the session id.

    :param connector: The Connector object
    :param verify: Boolean to check server certificate
    :return: User session token
    """
    login_url = f"{connector._get_phantom_base_url()}login"

    # Accessing the Login page
    r = requests.get(login_url, verify=verify)
    csrftoken = r.cookies["csrftoken"]

    data = {"username": os.environ.get("USERNAME"), "password": os.environ.get("PASSWORD"), "csrfmiddlewaretoken": csrftoken}

    headers = {"Cookie": f"csrftoken={csrftoken}", "Referer": login_url}

    # Logging into the Platform to get the session id
    r2 = requests.post(login_url, verify=verify, data=data, headers=headers)
    connector._set_csrf_info(csrftoken, headers["Referer"])
    return r2.cookies["sessionid"]


def create_container(connector, verify=False):
    """Create a container.

    :param connector: The Connector object
    :param verify: Boolean to check server certificate
    :return: Container id
    """
    sdi = uuid.uuid4()
    container = {"name": f"Added by unittest {sdi}", "label": "events", "source_data_identifier": f"{sdi}"}

    response = requests.post(
        f"{connector._get_phantom_base_url()}rest/container",
        verify=verify,
        auth=(os.environ.get("USERNAME"), os.environ.get("PASSWORD")),
        json=container,
    )

    return response.json()["id"]
