# File: dataminrpulse_config.py
#
# Copyright (c) 2023-2026 Dataminr
#
# This unpublished material is proprietary to Dataminr.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Dataminr.
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

import encryption_helper
import requests
from dotenv import load_dotenv


# Load '.env' file to the environment variables.
load_dotenv()

APPLICATION_VERSION = "6.4.1.361"
INTEGRATION_VERSION = "1.2.1"
CONTENT_TYPE = "application/json"
DEFAULT_ASSET_ID = "58"
DEFAULT_HEADERS = {"Content-Type": CONTENT_TYPE}
STATE_FILE_PATH = f"/opt/phantom/local_data/app_states/8630b723-b317-4765-b923-5be5229c71d1/{DEFAULT_ASSET_ID}_state.json"
ACTION_HEADER = {"Authorization": "Dmauth <dummy_token>"}
TOKEN_HEADER = {"Content-Type": "application/x-www-form-urlencoded"}
TOKEN_DATA = {"client_id": "<client_id>", "client_secret": "<dummy_client_secret>", "grant_type": "api_key"}

cipher_text = encryption_helper.encrypt("<dummy_client_secret>", DEFAULT_ASSET_ID)
CLIENT_SECRET_DUMMY_ENCRYPTED = encryption_helper.encrypt("test_value", DEFAULT_ASSET_ID)
CLIENT_DUMMY_ACTUAL = "test_value"

LIST_NAMES = "trackedAlerts"
QUERY = "Cyber Alerts"
PAGE_SIZE = 40
ALERT_TYPE = "All"

# V4 API Configuration
V4_DEFAULT_ASSET_ID = "58"
V4_API_VERSION = "v4"
V4_CLIENT_ID = "<v4_client_id>"
V4_CLIENT_SECRET = "<v4_client_secret>"
V4_LIST_NAMES = "test crest cyber"
V4_QUERY = "9374245408687001916"
V4_PAGE_SIZE = 1
V4_ALERT_TYPE = "All"
V4_DEFAULT_HEADERS = {"Content-Type": CONTENT_TYPE, "X-Application-Name": "splunk_soar"}
V4_TOKEN_HEADER = {"Content-Type": "application/x-www-form-urlencoded", "X-Application-Name": "splunk_soar"}
V4_ACTION_HEADER = {"Authorization": "Bearer <dummy_token>", "X-Application-Name": "splunk_soar"}
V4_STATE_FILE_PATH = f"/opt/phantom/local_data/app_states/8630b723-b317-4765-b923-5be5229c71d1/{V4_DEFAULT_ASSET_ID}_state.json"
V4_TOKEN_DATA = {"client_id": V4_CLIENT_ID, "client_secret": V4_CLIENT_SECRET, "grant_type": "api_key"}


# Encrypt v4 client secret for testing
v4_cipher_text = encryption_helper.encrypt(V4_CLIENT_SECRET, V4_DEFAULT_ASSET_ID)

TEST_JSON = {
    "action": "<action name>",
    "identifier": "<action_id>",
    "asset_id": DEFAULT_ASSET_ID,
    "config": {
        "appname": "-",
        "directory": "dataminrpulse-8630b723-b317-4765-b923-5be5229c71d1",
        "client_id": "<client_id>",
        "client_secret": cipher_text,
        "api_version": "v3",
        "main_module": "dataminrpulse_connector.py",
        "page_size_for_polling": PAGE_SIZE,
        "query": QUERY,
        "alert_type": ALERT_TYPE,
        "list_names": LIST_NAMES,
    },
    "ingest": {"container_label": "test", "interval_mins": "1", "poll": False, "polling_strategy": "off"},
    "main_module": "dataminrpulse_connector.py",
    "debug_level": 3,
    "dec_key": DEFAULT_ASSET_ID,
    "parameters": [{}],
}

# V4 API Test JSON Configuration
TEST_JSON_V4 = {
    "action": "<action name>",
    "identifier": "<action_id>",
    "asset_id": V4_DEFAULT_ASSET_ID,
    "config": {
        "appname": "-",
        "directory": "dataminrpulse-8630b723-b317-4765-b923-5be5229c71d1",
        "client_id": V4_CLIENT_ID,
        "client_secret": v4_cipher_text,
        "api_version": V4_API_VERSION,
        "main_module": "dataminrpulse_connector.py",
        "page_size_for_polling": V4_PAGE_SIZE,
        "query": V4_QUERY,
        "alert_type": V4_ALERT_TYPE,
        "list_names": V4_LIST_NAMES,
    },
    "ingest": {"container_label": "test", "interval_mins": "1", "poll": False, "polling_strategy": "off"},
    "main_module": "dataminrpulse_connector.py",
    "debug_level": 3,
    "dec_key": V4_DEFAULT_ASSET_ID,
    "parameters": [{}],
}

JSON_DATA = {
    "watchlists": {
        "TOPIC": [
            {"id": 3557389, "type": "TOPIC", "name": "test1", "description": "", "properties": {"watchlistColor": "darkblue"}},
        ],
    }
}

FILE_DATA = {
    "metadata": {
        "cyber": {
            "URLs": ["test[.]com", "test2[.]edu"],
            "addresses": [{"ip": "0.0.0[.]0", "port": "1977"}],
            "hashes": ["012345678907bc0f57057899d9ec929cee0aeee7769b75baa8faf26025c"],  # pragma: allowlist secret
        }
    }
}

ALERT_DATA = {
    "alertId": "85992181617703100451674976448185-1674976448217-1",
    "alertType": {"id": "alert", "name": "Alert", "color": "FFBB05"},
    "metadata": {
        "cyber": {
            "addresses": [{"ip": "77.73.133[.]62"}],
            "hashes": ["5f85677bb01576b77bc0f57057899d9ec929cee0aeee7769b75baa8faf26025c"],  # pragma: allowlist secret
            "malwares": ["Redline stealer"],
        }
    },
}

ALERT_DATA_CEF = {
    "alertId": "85992181617703100451674976448185-1674976448217-1",
    "alertType": {"id": "alert", "name": "Alert", "color": "FFBB05"},
    "metadata": [
        {
            "cyber": {
                "addresses": [{"ip": "77.73.133[.]62"}],
                "hashes": ["5f85677bb01576b77bc0f57057899d9ec929cee0aeee7769b75baa8faf26025c"],  # pragma: allowlist secret
                "malwares": ["Redline stealer"],
            }
        }
    ],
}

TOKEN_DUMMY_DMA_TOKEN_1 = "dummy value 1"
TOKEN_DUMMY_REFRESH_TOKEN_1 = "dummy value 1"

TOKEN_DUMMY_DMA_TOKEN_2 = "dummy value 2"
TOKEN_DUMMY_REFRESH_TOKEN_2 = "dummy value 2"

TOKEN_DUMMY_DMA_CIPHER_1 = encryption_helper.encrypt(TOKEN_DUMMY_DMA_TOKEN_1, DEFAULT_ASSET_ID)
TOKEN_DUMMY_REFRESH_CIPHER_1 = encryption_helper.encrypt(TOKEN_DUMMY_REFRESH_TOKEN_1, DEFAULT_ASSET_ID)

TOKEN_DUMMY_DMA_CIPHER_2 = encryption_helper.encrypt(TOKEN_DUMMY_DMA_TOKEN_2, DEFAULT_ASSET_ID)
TOKEN_DUMMY_REFRESH_CIPHER_2 = encryption_helper.encrypt(TOKEN_DUMMY_REFRESH_TOKEN_2, DEFAULT_ASSET_ID)
session_id = None


def set_state_file(dmaToken=False):
    """Save the state file as per requirement.

    :param dmaToken: True if access token is required in the state file
    """
    state_file = {
        "app_version": "2.0.0",
    }
    if dmaToken:
        state_file["token"] = {
            "dmaToken": encryption_helper.encrypt("<dummy_token>", DEFAULT_ASSET_ID),
            "refreshToken": encryption_helper.encrypt("<dummy_refresh_token>", DEFAULT_ASSET_ID),
            "expire": 33333333,
        }
    state_file = json.dumps(state_file)

    with open(STATE_FILE_PATH, "w+") as fp:
        fp.write(state_file)


def v4_set_state_file(dmaToken=False):
    """Save the state file as per requirement.

    :param dmaToken: True if access token is required in the state file
    """
    state_file = {
        "app_version": "2.0.0",
    }
    if dmaToken:
        state_file["token"] = {
            "dmaToken": encryption_helper.encrypt("<dummy_token>", V4_DEFAULT_ASSET_ID),
            "expire": 33333333,
        }
    state_file = json.dumps(state_file)

    with open(V4_STATE_FILE_PATH, "w+") as fp:
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

    data = {"username": "<username>", "password": "<password>", "csrfmiddlewaretoken": csrftoken}

    headers = {"Cookie": f"csrftoken={csrftoken}", "Referer": login_url}

    # Logging into the Platform to get the session id
    r2 = requests.post(login_url, verify=verify, data=data, headers=headers)
    connector._set_csrf_info(csrftoken, headers["Referer"])
    session_id = r2.cookies["sessionid"]
    return r2.cookies["sessionid"]
