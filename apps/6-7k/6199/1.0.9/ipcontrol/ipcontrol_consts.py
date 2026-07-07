# File: ipcontrol_consts.py
#
# Copyright (c) 2021 Splunk Inc.
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
IPCONTROL_ENDPOINT_LOGIN = '/login'
IPCONTROL_ENDPOINT = '/inc-rest/api/v1'
IPCONTROL_ENDPOINT_GET_CHILD_BLOCK = '/Exports/initExportChildBlock'
IPCONTROL_ENDPOINT_GET_HOSTNAME = '/Gets/getDeviceByIPAddr?ipAddress='
IPCONTROL_ENDPOINT_GET_BLOCK_TYPE = '/Exports/initExportChildBlock'
IPCONTROL_ENDPOINT_GET_IP_ADDRESS = '/Gets/getDeviceByHostname?hostname='

IPCONTROL_SUCC_TEST_CONNECTIVITY = 'Test Connectivity Passed'
IPCONTROL_ERR_TEST_CONNECTIVITY = 'Test Connectivity Failed'
IPCONTROL_ERR_NO_DATA_FOUND = 'No data found for parameter'
