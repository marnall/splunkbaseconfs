# File: extrahop_consts.py
#
# Copyright (c) 2018-2026 ExtraHop
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

# Tokens and state file
EXTRAHOP_OAUTH_TOKEN_STRING = "token"
EXTRAHOP_OAUTH_ACCESS_TOKEN_STRING = "access_token"
EXTRAHOP_OAUTH_ACCESS_TOKEN_IS_ENCRYPTED = "is_encrypted"
EXTRAHOP_DECRYPTION_ERROR = "Error occurred while decrypting the state file"
EXTRAHOP_ENCRYPTION_ERROR = "Error occurred while encrypting the state file"
EXTRAHOP_DETECTION_LAST_INGESTED_TIME = "detection_last_ingested_time"
EXTRAHOP_METRICS_LAST_INGESTED_TIME = "metrics_last_ingested_time"
EXTRAHOP_PACKETS_LAST_INGESTED_TIME = "packets_last_ingested_time"
EXTRAHOP_MARKDOWN_REGEX = r"(\[[^\]]+\]\(\#\/[^\)]+\))+"
EXTRAHOP_DETECTION_OBJECT_VALUE = "object_value"
EXTRAHOP_DETECTION_OBJECT_ID = "object_id"
EXTRAHOP_DEFAULT_DETECTION_CATEGORY = "sec.attack"

# Error and status messages
EXTRAHOP_ERROR_MESSAGE_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
EXTRAHOP_DEBUG_REST_ENDPOINT = "Making REST call to {}"
EXTRAHOP_STATE_FILE_CORRUPT_ERROR = (
    "Error occurred while loading the state file due to its unexpected format. Resetting the state file with the default format."
)
EXTRAHOP_CONTAINER_LIMIT_ERROR = "Container count should be greater than or equal to the number of object_ids"
EXTRAHOP_METRIC_REQUIRED_PARAM = "Required parameters: metric_cycle_length, object_type, object_id, metric_category and metric_name"
EXTRAHOP_METRIC_REQUIRED_API_PARAM = "API required parameters: cycle, object_type, object_ids, metric_category and metric_specs"
EXTRAHOP_METRIC_NOT_NEEDED_MESSAGE = "For asset_id: {}, Interval should be in multiples of cycle length"
EXTRAHOP_DEFAULT_ERROR = "Error : {}"
EXTRAHOP_CORRUPTED_KEY_MESSAGE = "Corrupted key {}"
EXTRHOP_CONTAINER_ERROR_MESSAGE = "Error occurred while saving the container: ID {}: {}"
EXTRHOP_ARTIFACT_ERROR_MESSAGE = "Error occurred while saving the artifact(s): {}"
EXTRAHOP_ARTIFACT_SAME_SDI = "Artifact already exist with SDI ({}). Hence skipping the ingestion for container with id {}"

# Endpoints
EXTRAHOP_TOKEN_ENDPOINT = "/oauth2/token"
EXTRAHOP_DEVICES_ENDPOINT = "/api/v1/devices/search"
EXTRAHOP_DEVICE_WITH_ID_ENDPOINT = "/api/v1/devices/{}"
EXTRAHOP_BASIC_DETAILS_ENDPOINT = "/api/v1/extrahop"
EXTRAHOP_ACTIVITY_MAP_ENDPOINT = "/api/v1/activitymaps/query"
EXTRAHOP_CUSTOM_DEVICES_ENDPOINT = "/api/v1/customdevices"
EXTRAHOP_TAGS_ENDPOINT = "/api/v1/tags"
EXTRAHOP_TAG_TO_DEVICE_ENDPOINT = "/api/v1/tags/{}/devices"
EXTRAHOP_DETECTIONS_ENDPOINT = "/api/v1/detections/search"
EXTRAHOP_METRICS_ENDPOINT = "/api/v1/metrics"
EXTRAHOP_METRICS_TOTAL_ENDPOINT = "/api/v1/metrics/total"
EXTRAHOP_METRICS_XID_ENDPOINT = "/api/v1/metrics/next/{}"
EXTRAHOP_PACKET_SEARCH_ENDPOINT = "/api/v1/packets/search"
EXTRAHOP_SOAR_ARTIFACT_ENDPOINT = "/artifact?_filter_container__in=[{}]"

# Default values
EXTRAHOP_DEFAULT_TIMEOUT = 30
EXTRAHOP_DEFAULT_LIMIT = 1000
EXTRAHOP_DETECTION_DEFAULT_INTERVAL = 3600
EXTRAHOP_METRICS_DEFAULT_INTERVAL = 3600
EXTRAHOP_PACKETS_DEFAULT_INTERVAL = 3600

# Constant values
EXTRAHOP_INSTANCE_CLOUD = "Reveal(x) 360"
EXTRAHOP_INSTANCE_ON_PREM = "Reveal(x) Enterprise"
EXTRAHOP_INVALID_CLIENT_MESSAGE = 'Status Code: 400 Data from server: {"error":"invalid_client"}'
EXTRAHOP_ACTION_HANDLER_MESSAGE = "In action handler for: {0}"
EXTRAHOP_INVALID_FILTER_MESSAGE = "Unable to parse JSON for '{}' parameter"
EXTRAHOP_RETRIEVING_DATA_MESSAGE = "Retrieving {} from Extrahop"
EXTRAHOP_INGESTION_MESSAGE = "{} id ({}) is ingested in container id ({})"
EXTRAHOP_INGESTION_START_MESSAGE = "Ingesting the data"
EXTRAHOP_DUPLICATE_CONTAINER_MESSAGE = "Duplicate container found"
EXTRAHOP_EXPIRED_TOKEN_MESSAGES = [
    "Status Code: 400 Data from server: The specified access token is invalid",
    'Status Code: 401 Data from server: {"error_message": "Error getting user from bearer token"}',
    "Status Code: 400 Data from server: invalid",
    'Status Code: 401 Data from server: {"error_message":"Invalid access token"}',
]

# Validation for value_list
EXTRAHOP_PEER_ROLE_LIST = ["client", "server", "any"]
EXTRAHOP_FIELD_TYPE_LIST = ["custom_filter", "ipaddr", "macaddr", "vendor", "tag"]
EXTRAHOP_INGESTION_TYPE_LIST = ["Detections", "Metrics", "PCAP"]
EXTRAHOP_INGESTION_DETECTION_KEYS = ["json_object", "detection_category", "detection_status"]
EXTRAHOP_INGESTION_METRICS_KEYS = ["json_object", "metric_cycle_length", "object_type", "object_id", "metric_category", "metric_name"]
EXTRAHOP_INGESTION_METRICS_API_KEYS = ["cycle", "metric_category", "metric_specs", "object_ids", "object_type"]
EXTRHOP_CYCLE_SELECTION = ["auto", "30sec", "5min", "1hr"]
EXTRHOP_METRIC_OBJECT_TYPE = ["Device", "Device Group", "Device Group Summary", "Application", "Network"]
EXTRAHOP_INGESTION_PACKETS_KEYS = ["json_object", "bpf", "limit_bytes", "limit_search_duration", "ip1", "ip2", "port1", "port2"]
EXTRAHOP_STATUS_LIST = [".none", "in_progress", "new", "closed", "acknowledged"]
EXTRAHOP_INVALID_SELECTION = "Invalid '{0}' selected. Must be one of: {1}."
EXTRAHOP_INVALID_STATUS = "Invalid '{0}'. Must be one of: {1}."

# Constants relating to 'validate_integer'
EXTRAHOP_VALID_INT_MESSAGE = "Please provide a valid integer value in the '{param}'"
EXTRAHOP_NON_NEG_NON_ZERO_INT_MESSAGE = "Please provide a valid non-zero positive integer value in '{param}'"
EXTRAHOP_NON_NEG_INT_MESSAGE = "Please provide a valid non-negative integer value in the '{param}'"
EXTRAHOP_PARAM_VALIDATION_MESSAGE = "Validating the parameters"

EXTRAHOP_EH_API_ID_KEY = "eh_api_id"
EXTRAHOP_MINUTES_KEY = "minutes"
EXTRAHOP_OFFSET_KEY = "offset"
EXTRAHOP_LIMIT_KEY = "limit"
EXTRAHOP_VERIFY_SERVER_FAIL = False

# Objects
EXTRAHOP_OBJECT_TYPE = {
    "Device": "device",
    "Device Group": "device_group",
    "Device Group Summary": "device_group",
    "Application": "application",
    "Network": "network",
}

EXTRAHOP_VTYPE = {"count": "dcount", "dmax": "dcount", "dset": "ddset", "max": "dmax", "tset": "tset", "time": "time", "snap": "dsnap"}
