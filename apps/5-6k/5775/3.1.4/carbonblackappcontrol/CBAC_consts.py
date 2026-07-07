# File: CBAC_consts.py
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
ERROR_PARSING_JSON = "Error parsing the response as JSON"
CBAPPCONTROL_JSON_BASE_URL = "base_url"
CBAPPCONTROL_JSON_API_TOKEN = "api_token"
CBAPPCONTROL_JSON_DESCRIPTION = "comment"
CBAPPCONTROL_JSON_UNBLOCK_STATE = "file_state"

FILE_CATALOG_ENDPOINT = "/filecatalog"
FILE_RULE_ENDPOINT = "/fileRule"
FILE_UPLOAD_ENDPOINT = "/fileUpload"
FILE_INSTANCE_ENDPOINT = "/fileInstance"
COMPUTER_OBJECT_ENDPOINT = "/computer"
POLICY_OBJECT_ENDPOINT = "/policy"
CAT_ID_DATA = "fileCatalogId:%s"
APPEND_HASHES = "%s:%s"
LISTDECISION_MAP = {"white": "2", "black": "3"}
APPEND_NOT_POLICY = "%s%s"
CBAPPCONTROL_FID = "id"
DECISION_MAP = {"local_approval": "localState", "global_approval": "fileState"}
CBAPPCONTROL_API_URI = "/api/bit9platform/v1"
CBAPPCONTROL_LIST_FILES_SUCC = "Number of files returned: {0}"
CBAPPCONTROL_LIST_POLICIES_SUCC = "Number of policies returned: {0}"
CBAPPCONTROL_GET_FILE_SUCC = "Successfully added file to vault. Vault ID: {0}"

CBAPPCONTROL_ERROR_FROM_SERVER = "API failed, Status code: {status}, Detail: {detail}"
CBAPPCONTROL_ERROR_JSON_PARSE = "Unable to parse reply as a Json, raw string reply: '{raw_text}'"
CBAPPCONTROL_ERROR_API_UNSUPPORTED_METHOD = "Unsupported method"
CBAPPCONTROL_ERROR_SERVER_CONNECTION = "Connection failed"

CBAPPCONTROL_FILE_STATE_UNAPPROVED = "1"
CBAPPCONTROL_FILE_STATE_APPROVED = "2"
CBAPPCONTROL_FILE_STATE_BANNED = "3"

CBAPPCONTROL_LOCAL_STATE_UNAPPROVED = "1"
CBAPPCONTROL_LOCAL_STATE_APPROVED = "2"

CBAPPCONTROL_UNBLOCK_STATE_MAP = {"approved": CBAPPCONTROL_FILE_STATE_APPROVED, "unapproved": CBAPPCONTROL_FILE_STATE_UNAPPROVED}
CBAPPCONTROL_UNBLOCK_LOCAL_STATE_MAP = {"approved": CBAPPCONTROL_LOCAL_STATE_APPROVED, "unapproved": CBAPPCONTROL_LOCAL_STATE_UNAPPROVED}
CBAPPCONTROL_DEFAULT_UNBLOCK_STATE = "unapproved"
CBAPPCONTROL_ADDED_BY_PHANTOM = "Added by Phantom Installation ID: {0}"

CBAPPCONTROL_INVALID_INT = "Please provide a valid integer value in the {param}"
CBAPPCONTROL_ERROR_NEGATIVE_INT_PARAM = "Please provide a valid non-negative integer value in the {param}"
CBAPPCONTROL_ERROR_INVALID_PARAM = "Please provide a non-zero positive integer in the {param}"

ERROR_MESSAGE_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"

CBAPPCONTROL_DEFAULT_TIMEOUT = 60
