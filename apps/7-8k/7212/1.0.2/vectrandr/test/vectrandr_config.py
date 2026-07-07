# File: vectrandr_config.py
#
# Copyright (c) 2024-2025 Vectra
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

import os
import uuid

import encryption_helper
import requests
from dotenv import load_dotenv


# Load '.env' file to the environment variables.
load_dotenv()

CONTENT_TYPE = "application/json"
CONTENT_HTML_TYPE = "text/html"
DEFAULT_ASSET_ID = "10"
APP_ID = "93878b88-0aad-45de-9505-8602deeab5e8"
DEFAULT_HEADERS = {"Content-Type": CONTENT_TYPE}
STATE_FILE_PATH = f"/opt/phantom/local_data/app_states/{APP_ID}/{DEFAULT_ASSET_ID}_state.json"
USER_AGENT = "VectraNDR-SplunkSOAR-1.0.0"
DUMMY_BASE_URL = "https://1234567891243.uw2.portal.vectra.ai"
MAIN_MODULE = "vectrandr_connector.py"
session_id = None

cipher_text = encryption_helper.encrypt("<dummy_api_token>", DEFAULT_ASSET_ID)

ACTION_HEADER = {"Authorization": "Token <dummy_api_token>", "User-agent": USER_AGENT}
TOKEN_HEADER = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json", "User-agent": USER_AGENT}

TEST_JSON = {
    "action": "<action name>",
    "identifier": "<action_id>",
    "asset_id": DEFAULT_ASSET_ID,
    "config": {
        "appname": "-",
        "directory": "vectracognitodetectsplunksoar_93878b88-0aad-45de-9505-8602deeab5e8",
        "base_url": DUMMY_BASE_URL,
        "verify_server_certificate": False,
        "api_token": cipher_text,
        "main_module": MAIN_MODULE,
    },
    "main_module": MAIN_MODULE,
    "debug_level": 3,
    "dec_key": DEFAULT_ASSET_ID,
    "parameters": [{}],
}


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
