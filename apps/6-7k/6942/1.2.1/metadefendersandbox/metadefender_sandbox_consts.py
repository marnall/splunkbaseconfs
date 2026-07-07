# File: opswatfilescan_consts.py
#
# Copyright (c) OPSWAT, 2024
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

# Endpoints
METADEFENDER_SANDBOX_ENDPOINT_USERINFO = '/api/users/me'
METADEFENDER_SANDBOX_ENDPOINT_SCAN_FILE = '/api/scan/file'
METADEFENDER_SANDBOX_ENDPOINT_SCAN_URL = '/api/scan/url'
METADEFENDER_SANDBOX_ENDPOINT_SCAN_POLL = '/api/scan/{id}/report?{filters}'
METADEFENDER_SANDBOX_ENDPOINT_SERACH = '/api/reports/search'
METADEFENDER_SANDBOX_ENDPOINT_REPUTATION = '/api/reputation'

METADEFENDER_SANDBOX_POLL_INTERVAL_MIN = 1
METADEFENDER_SANDBOX_TIMEOUT_MIN = 30
METADEFENDER_SANDBOX_POLL_INTERVAL_MAX = 30
METADEFENDER_SANDBOX_TIMEOUT_MAX = 300
