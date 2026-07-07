# File: salesforce_consts.py
#
# Copyright (c) 2017-2026 Splunk Inc.
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
PHANTOM_SYS_INFO_URL = "{url}rest/system_info"
PHANTOM_ASSET_INFO_URL = "{url}rest/asset/{asset_id}"


SALESFORCE_OAUTH_AUTHORIZE_PATH = "/services/oauth2/authorize"
SALESFORCE_OAUTH_TOKEN_PATH = "/services/oauth2/token"

URL_GET_CODE = f"https://login.salesforce.com{SALESFORCE_OAUTH_AUTHORIZE_PATH}"
URL_GET_TOKEN = f"https://login.salesforce.com{SALESFORCE_OAUTH_TOKEN_PATH}"

URL_GET_CODE_TEST = f"https://test.salesforce.com{SALESFORCE_OAUTH_AUTHORIZE_PATH}"
URL_GET_TOKEN_TEST = f"https://test.salesforce.com{SALESFORCE_OAUTH_TOKEN_PATH}"


API_ENDPOINT_DESCRIBE_GLOBAL = "{version}/sobjects/"
API_ENDPOINT_GET_UPDATED = "{version}/sobjects/{sobject}/updated/"
API_ENDPOINT_OBJECT_ID = "{version}/sobjects/{sobject}/{id}/"
API_ENDPOINT_RUN_QUERY = "{version}/{query_type}/"
API_ENDPOINT_OBJECT = "{version}/sobjects/{sobject}/"
API_ENDPOINT_GET_LISTVIEWS = "{version}/sobjects/{sobject}/listviews/"
API_ENDPOINT_GET_LISTVIEW_LOCATOR = "{version}/sobjects/{sobject}/listviews/{locator}/"
API_ENDPOINT_BATCH_REQUEST = "{version}/composite/batch/"
API_ENDPOINT_GET_LISTVIEWS_FROM_OBJECT = "{version}/ui-api/list-records/{sobject}/{view_name}"

CASE_FIELD_MAP = {
    "parent_case_id": "ParentId",
    "subject": "Subject",
    "priority": "Priority",
    "description": "Description",
    "status": "Status",
    "closed": "IsClosed",
    "escalated": "IsEscalated",
}
SALESFORCE_INVALID_INTEGER = 'Please provide non-zero positive integer in "{parameter}"'
SALESFORCE_UNKNOWN_ERR_MSG = "Unknown error occurred. Please check the asset configuration and|or action parameters."
SALESFORCE_ERR_CODE_UNAVAILABLE = "Error code unavailable"
SALESFORCE_DEFAULT_TIMEOUT = 30

# Number of random bytes used to generate the PKCE code_verifier (RFC 7636).
SALESFORCE_PKCE_VERIFIER_BYTES = 96
