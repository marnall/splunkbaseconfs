# File: phishinginitiative_consts.py
#
# Copyright (c) 2017-2025 Splunk Inc.
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
PHISINIT_JSON_URL = "url"
PHISINIT_JSON_BASE_URL = "base_url"
PHISINIT_JSON_API_KEY = "api_key"  # pragma: allowlist secret

PHISINIT_ERROR_CONNECTIVITY_TEST = "Test connectivity failed"
PHISINIT_SUCCESS_CONNECTIVITY_TEST = "Test connectivity passed"
PHISINIT_ERROR_FROM_SERVER = "API failed, Status code: {status}, Detail: {detail}"

PHISINIT_LOOKUP_URL = "/api/v1/urls/lookup"

PHISINIT_ERROR_SERVER_CONNECTIVITY = "Error connecting to server. Error: {}"
PHISINIT_USING_BASE_URL = "Using Base URL: {0}"

PHISINIT_DEFAULT_REQUEST_TIMEOUT = 30  # in seconds
