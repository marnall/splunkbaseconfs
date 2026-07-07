# File: mfeesm_consts.py
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
# ESM_JSON_POLL_HOURS = "poll_hours"
ESM_JSON_POLL_TIME = "poll_time"
ESM_JSON_LAST_DATE_TIME = "last_date_time"
ESM_JSON_TIMEZONE = "timezone"
ESM_JSON_MAX_CONTAINERS = "max_containers"
ESM_JSON_FIRST_MAX_CONTAINERS = "first_run_max_events"
ESM_JSON_FILTERS = "filters"
ESM_JSON_QUERY_TIMEOUT = "query_timeout"
ESM_TEST_CONNECTIVITY_FAILED = "Test Connectivity failed"
ESM_TEST_CONNECTIVITY_PASSED = "Test connectivity Passed"

ERR_CODE_UNAVAILABLE = "Error code unavailable"
ERR_MSG_UNAVAILABLE = "Unknown error occurred. Please check the action parameters."

ESM_ROWS_INFO = "Getting all containers with the same date, down to the second. " \
                  "That means the device is generating max_containers=({0}) per second. Skipping to the next second to not get stuck."
ESM_BASE_URL = "{0}/rs/esm/"
ESM_VER_2 = 'v2/'
ESM_QUERY_GET_FILTER_ENDPOINT = 'qryGetFilterFields'
ESM_UPDATE_WATCHLIST_ENDPOINT = 'sysAddWatchlistValues'
ESM_WATCHLIST_ENDPOINT = 'sysGetWatchlists'
ESM_WATCHLIST_DETAILS_ENDPOINT = 'sysGetWatchlistDetails'
ESM_WATCHLIST_DETAILS_LIMIT_ENDPOINT = 'sysGetWatchlistValues?pos=0&count=50000'
ESM_WATCHLIST_ENDPOINT_10 = '?hidden=true&dynamic=true&writeOnly=true&indexedOnly=true'
GET_STATUS_URL = "qryGetStatus"
GET_EVENTS_URL = "qryGetCorrEventDataForID?queryType=EVENT"
TEST_QUERY = "qryGetSelectFields?type=EVENT&groupType=NO_GROUP"
EXECUTE_QUERY_URL = "qryExecuteDetail?type=EVENT&reverse=false"
GET_ALARMS_URL = "alarmGetTriggeredAlarms"
GET_RESULTS_URL = "qryGetResults?startPos=0&numRows=1000000&reverse=false"

CEF_MAP = {"dstMac": "destinationMacAddress", "dstIP": "destinationAddress", "srcIP": "sourceAddress", "srcMac": "sourceMacAddress"}
QUERY_MAX_WAIT_TIME = 5
CEF_EXCLUDE = [u'', '', "0", u'0']
ID_DICT = {'name': 'Alert.ID'}
FIRST_DICT = {'name': 'Alert.FirstTime'}
MSG_DICT = {'name': 'Rule.msg'}
DEFAULT_FIELD_LIST = ["LastTime", "Rule.msg", "DSIDSigID", "SrcIP", "DstIP"]
cef_field_list = ['startTime', 'destinationUserName', 'destinationAddress', 'destinationMacAddress',
        'destinationPort', 'receiptTime', 'transportProtocol', 'sourceMacAddress',
        'sourcePort', 'applicationProtocol', 'deviceExternalId', 'sourceUserName',
        'sourceAddress', 'fileHash', 'message', 'src', 'sourceUserId', 'filePath',
        'fileSize', 'fileType', 'fileName', 'bytesIn', 'bytesOut', 'requestCookies',
        'destinationUserId', 'destinationHostName', 'deviceAddress']
CREATE_CONTAINER_RESPONSE = "save_container returns, value: {0}, reason: {1}, id: {2}"
ESM_DEFAULT_TIMEOUT_SECS = 20
ESM_QUERY_TIMEOUT_ERR = "Query not completed in the configured time. Please increase the query_timeout " \
                          "value in the asset config and try again."

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
ESM_RESP_DATETIME_FORMAT = "%m/%d/%Y %H:%M:%S"

ESM_DEFAULT_MAX_CONTAINERS = 10
ESM_CEF_CONTAINS = {
        'nDDeviceNDDevIDDstManagementIP': ['ip'],
        'nDDeviceNDDevIDSrcManagementIP': ['ip'],
        'alertDstIP': ['ip'],
        'alertSrcIP': ['ip'],
        'alertDstMac': ['mac address'],
        'alertSrcMac': ['mac address'],
        'userIDSrc': ['user name'],
        'alertAlertID': ['esm event id']}
ESM_POLL_TIME_DEFAULT = "2"
