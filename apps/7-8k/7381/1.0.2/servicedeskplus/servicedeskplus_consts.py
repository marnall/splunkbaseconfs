# File: servicedeskplus_consts.py
#
# Copyright (c) Splunk Inc., 2024-2026
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

SDP_BACKFILL_DAYS = 7

SDP_TICKET_ARTIFACT_LABEL = "servicedeskplus_ticket"
SDP_TICKET_JSON_ID = "id"

SDP_DATA_CENTERS = {
    "United States": {"base_url": "https://sdpondemand.manageengine.com", "oauth": "https://accounts.zoho.com/oauth/v2/token"},
    "Europe": {"base_url": "https://sdpondemand.manageengine.eu", "oauth": "https://accounts.zoho.eu/oauth/v2/token"},
    "India": {"base_url": "https://sdpondemand.manageengine.in", "oauth": "https://accounts.zoho.in/oauth/v2/token"},
    "China": {"base_url": "https://servicedeskplus.cn", "oauth": "https://accounts.zoho.com.cn/oauth/v2/token"},
    "Australia": {"base_url": "https://servicedeskplus.net.au", "oauth": "https://accounts.zoho.com.au/oauth/v2/token"},
    "Japan": {"base_url": "https://servicedeskplus.jp", "oauth": "https://accounts.zoho.com.jp/oauth/v2/token"},
    "Canada": {"base_url": "https://servicedeskplus.ca", "oauth": "https://accounts.zoho.ca/oauth/v2/token"},
    "United Kingdom": {"base_url": "https://servicedeskplus.uk", "oauth": "https://accounts.zoho.uk/oauth/v2/token"},
}

REQUEST_FIELDS = [
    "subject",
    "description",
    "request_type",
    "impact",
    "template",
    "status",
    "mode",
    "level",
    "urgency",
    "priority",
    "service_category",
    "requester",
    "assets",
    "site",
    "group",
    "technician",
    "category",
    "subcategory",
    "item",
    "email_ids_to_notify",
    "is_fcr",
    "resources",
    "udf_fields",
    "update_reason",
]

FIELDS_WITH_NAME = [
    "request_type",
    "impact",
    "status",
    "mode",
    "level",
    "urgency",
    "priority",
    "service_category",
    "requester",
    "site",
    "group",
    "technician",
    "category",
    "subcategory",
    "item",
]

API_GET_REQUESTS = "/api/v3/requests"
API_DELETE_ENDPOINT = {"onprem": "/move_to_trash", "cloud": ""}
API_ASSIGN_ENDPOINT = {"onprem": "assign", "cloud": "_assign"}
API_CLOSE_ENDPOINT = {"onprem": "close", "cloud": "_close"}

# Constants relating to 'get_error_message_from_exception'
ERR_MSG_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters."
PARSE_ERR_MSG = "Unable to parse the error message. Please check the asset configuration and|or action parameters."

# Constants relating to 'validate_integer'
SDP_VALID_INT_MSG = "Please provide a valid integer value in the {param}"
SDP_NON_NEG_NON_ZERO_INT_MSG = "Please provide a valid non-zero positive integer value in {param}"
SDP_NON_NEG_INT_MSG = "Please provide a valid non-negative integer value in the {param}"
SDP_START_INDEX_KEY = "'start_index' action parameter"
SDP_MAX_RESULTS_KEY = "'max_results' action parameter"
SDP_CONTAINER_COUNT_KEY = "'Maximum containers' configuration parameter"
SDP_CONTAINER_FOUND_MSG = "Found container id: {cid}"
SDP_CONTAINER_UPDATE_MSG = "Updating existing ticket container"
SDP_SUCCESS_MSG = "Successfully received a response from server"
SDP_SUCCESS_UPDATE_MSG = "Successfully updated ticket"

# Constants relating to error messages
SDP_ERR_EMPTY_RESPONSE = "Status Code {code}. Empty response and no information in the header."
SDP_ERR_UNABLE_TO_PARSE_HTML_RESPONSE = "Unable to parse HTML response. {error}"
SDP_ERR_UNABLE_TO_PARSE_JSON_RESPONSE = "Unable to parse response as JSON. {error}"
SDP_ERR_CONNECTIVITY_FAILURE = "Failed to connect to server"
SDP_EXCEPTION_ERR_MSG = "{msg}. {error}"
SDP_ERR_ILLEGAL_FORMAT = "Illegal {name} format. Input format should be a string of key and value separated by: \
    Multiple key;value pairs can be given, separated with a comma"
SDP_ERR_CONTAINERS_UNABLE = "Unable to query SOAR for containers: {error}"
SDP_ERR_NO_CONTAINERS = "No container matched"
SDP_ERR_CONTAINER_WRONG = "Container results are not proper: {error}"
SDP_ERR_CONTAINER_UPDATE = "Error while updating the container: {err}"
SDP_ERR_CONTAINER_FAILURE = "Could not save new ticket container"
SDP_ERR_FETCHING_TICKET = "Error occurred while fetching ticket {ticket_id}: {error}"
SDP_ERR_FETCHING_TICKETS = "Error occurred while fetching tickets: {error}"
SDP_ERR_RETRIEVE_TICKETS = "Could not retrieve tickets"
SDP_ERR_INVALID_CONFIGURATION = "ServiceDesk Plus is [On-Premises]: please provide its Server URL"
SDP_ERR_NO_VALUE = "Could not extract value '{value}' from fetched requests."
SDP_ERR_NOT_IMPLEMENTED = "Integration with ManageEngine ServiceDesk Plus Cloud not available yet."

# JSON returned from ManageEngine
# SDP_JSON_ACCESS_TOKEN = "access_token"
SDP_JSON_LIST_INFO = "list_info"
