# File: symanteccas_consts.py
#
# Copyright (c) 2016-2022 Splunk Inc.
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
#
SYMANTECCAS_JSON_API_KEY = 'api_key'  # pragma: allowlist secret
SYMANTECCAS_JSON_URL = 'url'
SYMANTECCAS_JSON_VERIFY_SERVER_CERT = 'verify_server_cert'
SYMANTECCAS_JSON_TIMEOUT_SECS = 'timeout'
SYMANTECCAS_JSON_VAULT_ID = 'vault_id'
SYMANTECCAS_JSON_FILE_NAME = 'file_name'
SYMANTECCAS_JSON_INVALID_TIMEOUT = 'Timeout should be non-zero positive number'
SYMANTECCAS_JSON_RESP_ERROR = 'error'
SYMANTECCAS_JSON_RESP_RESULT = 'result'
SYMANTECCAS_JSON_RESP_STATUS = 'status'
SYMANTECCAS_JSON_RESP_ID = 'id'
SYMANTECCAS_JSON_RESP_SCORE = 'score'
SYMANTECCAS_DEFAULT_TIMEOUT = 60
SYMANTECCAS_X_API_TOKEN = 'X-API-TOKEN'
SYMANTECCAS_CONNECTION_TEST_MSG = "Querying endpoint to test the connectivity"
SYMANTECCAS_BASE_URL = "{url}/rapi"
SYMANTECCAS_DETONATE_FILE_ENDPOINT = "/cas/scan"
SYMANTECCAS_TEST_CONN_ENDPOINT = "{websocket_url}/rapi/ws/cas_task"
SYMANTECCAS_TEST_CONN_TIMEOUT = 5
SYMANTECCAS_ERR_API_UNSUPPORTED_METHOD = 'Unsupported method : {method}'
SYMANTECCAS_ERR_SERVER_CONNECTION = 'Connection failed'
SYMANTECCAS_SOCKET_ERR_ACCESS_DENIED = 'Access denied'
SYMANTECCAS_CONNECTIVITY_SUCC = 'Connectivity succeeded'
SYMANTECCAS_CONNECTIVITY_FAIL = 'Connectivity failed'
SYMANTECCAS_TEST_CONN_OVERRIDE_TIMEOUT = 'Overriding websocket timeout for test connectivity'
SYMANTECCAS_ERR_JSON_PARSE = 'Unable to parse the fields parameter into a ' \
                             'dictionary. Response text - {raw_text}'
SYMANTECCAS_ERR_FROM_SERVER = 'API failed, Status code: {status}, ' \
                              'Detail: {detail}'
SYMANTECCAS_REST_RESP_SUCCESS = 200
SYMANTECCAS_REST_RESP_RESOURCE_INCORRECT = 400
SYMANTECCAS_REST_RESP_RESOURCE_INCORRECT_MSG = 'Invalid input. The resource '\
                                               ' is in an incorrect format'
SYMANTECCAS_REST_RESP_ACCESS_DENIED = 403
SYMANTECCAS_REST_RESP_ACCESS_DENIED_MSG = 'Access denied. The API key was ' \
                                          'successfully authenticated, but the' \
                                          ' license does not permit access to ' \
                                          'the requested resource'
SYMANTECCAS_REST_RESP_RESOURCE_NOT_FOUND = 404
SYMANTECCAS_REST_RESP_RESOURCE_NOT_FOUND_MSG = 'Data not available'
SYMANTECCAS_REST_RESP_OTHER_ERROR_MSG = "Unknown error"
SYMANTECCAS_TEST_CONN_LOGIN = 'Logging to sandbox '
SYMANTECCAS_UNKNOWN_VAULT_ID = 'File not found in vault ("{vault_id}")'
SYMANTECCAS_ERR_WAITING_REPORT = 'Unable to parse the fields parameter into a ' \
                                 'dictionary. Response text: {raw_text}'
SYMANTECCAS_ERR_UNABLE_FULFILL_REQ = 'Content Analysis was unable to fulfill the request'
SYMANTECCAS_ERR_UNABLE_FULFILL_REQ_WITH_ERROR = 'Content Analysis was unable to fulfill the request : {error}'
SYMANTECCAS_ERR_WEBSOCKET_TIMEOUT = 'Unable to receive any response until timeout'
SYMANTECCAS_ERR_WEBSOCKET_NO_RESPONSE = 'Unable to receive the expected report after retrying 10 times'
SYMANTECCAS_ERR_WEBSOCKET = "Error while websocket communication"
SYMANTECCAS_STATUS_ERROR = 2
SYMANTECCAS_STATUS_COMPLETE = 1
SYMANTECCAS_STATUS_COMPLETE_WITH_ERROR = 3
SYMANTECCAS_STATUS_MAX_POLLING_COUNT = 10
ERR_CODE_MSG = "Error code unavailable"
ERR_MSG_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
TYPE_ERR_MSG = "Error occurred while connecting to the Server. Please check the asset configuration and|or the action parameters"
