# File: pagerduty_consts.py
#
# Copyright (c) 2016-2024 Splunk Inc.
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
PAGERDUTY_JSON_BASEURL = "base_url"
PAGERDUTY_API_KEY = "api_token"  # pragma: allowlist secret

# Deprecated as of v2
# PAGERDUTY_API_URI = "/api/v1"


PAGERDUTY_ERR_QUERY = "PagerDuty query failed"
PAGERDUTY_SUCC_QUERY = "PagerDuty query successful"
PAGERDUTY_ERR_QUERY_RETURNED_NO_DATA = "PagerDuty query did not return any information"
PAGERDUTY_ERR_SERVER_CONNECTION = "Connection to server failed"
PAGERDUTY_ERR_CONNECTIVITY_TEST = "Test Connectivity Failed"
PAGERDUTY_SUCC_CONNECTIVITY_TEST = "Test Connectivity Passed"
PAGERDUTY_DEFAULT_LIMIT = 25
