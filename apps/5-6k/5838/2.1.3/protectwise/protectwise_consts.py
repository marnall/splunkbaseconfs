# File: protectwise_consts.py
#
# Copyright (c) 2016-2025 Splunk Inc.
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
PROTECTWISE_JSON_AUTH_TOKEN = "auth_token"
PROTECTWISE_JSON_LAST_DATE_TIME = "last_date_time"
PROTECTWISE_JSON_POLL_HOURS = "poll_hours"
PROTECTWISE_JSON_ALLOW_ARTIFACT_DUPLICATES = "allow_duplicate_artifacts"
PROTECTWISE_JSON_ALLOW_CONTAINER_DUPLICATES = "allow_duplicate_containers"
PROTECTWISE_JSON_TYPE = "type"
PROTECTWISE_JSON_ID = "id"
PROTECTWISE_JSON_SENSOR_ID = "sensorid"
PROTECTWISE_JSON_MAX_CONTAINERS = "max_containers"
PROTECTWISE_JSON_START_TIME = "start_time"
PROTECTWISE_JSON_END_TIME = "end_time"
PROTECTWISE_JSON_IP = "ip"
PROTECTWISE_JSON_DOMAIN = "domain"
PROTECTWISE_JSON_HASH = "hash"

PROTECTWISE_ERR_INVALID_INT = "Please provide a valid {msg} integer value in the {param} parameter"
PROTECTWISE_ERR_SERVER_CONNECTION = "Error connecting to server"
PROTECTWISE_ERR_CODE_UNAVAILABLE = "Error code unavailable"
PROTECTWISE_ERR_MSG_UNAVAILABLE = "Unknown error occurred. Please check the asset configuration and|or action parameters."
PROTECTWISE_ERR_PARSE_JSON_RESPONSE = "Unable to parse response as JSON: {}"
PROTECTWISE_ERR_SERVER = "Error from server. Status code: {0}, Details: {1}"

PROTECTWISE_BASE_URL = "https://api.protectwise.com/api/v1"
PROTECTWISE_ERR_API_UNSUPPORTED_METHOD = "Unsupported requests method: '{method}' specified"
PROTECTWISE_PROG_FINISHED_DOWNLOADING_STATUS = "Finished downloading {0:.0%}"

PROTECTWISE_CEF_CONTAINS = {"observationId": ["protectwise observation id"], "sensorId": ["protectwise sensor id"]}
VALID_PROTECTWISE_TYPES = ["event", "observation"]
PROTECTWISE_N_DAYS_HOURS = 5 * 24

# actions that this app supports
ACTION_ID_GET_PACKETS = "get_packets"
ACTION_ID_HUNT_IP = "hunt_ip"
ACTION_ID_HUNT_DOMAIN = "hunt_domain"
ACTION_ID_HUNT_FILE = "hunt_file"
ACTION_ID_TEST_ASSET_CONNECTIVITY = "test_asset_connectivity"
PROTECTWISE_DEFAULT_TIMEOUT = 30
PROTECTWISE_DEFAULT_NUMBER_OF_RETRIES = 3
PROTECTWISE_WAIT_NUMBER_OF_SECONDS = 120
