# Copyright (c) 2026 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# API Configuration
DEFAULT_TIMEOUT = 30
TEST_DOMAIN = "example.com"

# API Endpoints
ENDPOINT_SSL_INFO = "v2/ssl-info"
ENDPOINT_IP_REPUTATION = "v2/ip-reputation"
ENDPOINT_DOMAIN_REPUTATION = "v2/domain-reputation"

# Headers
HEADER_API_KEY = "x-api-key"  # pragma: allowlist secret
HEADER_CONTENT_TYPE = "Content-Type"
CONTENT_TYPE_JSON = "application/json"

# JSON Response Keys
KEY_CERTIFICATE = "certificate"
KEY_BLACKLISTS = "blacklists"
KEY_ENGINES = "engines"

# Log Messages
MSG_CONNECTING_TO_SERVER = "Connecting to APIVoid v2 server"
MSG_TEST_CONNECTIVITY_PASSED = "Test connectivity passed"
MSG_TEST_CONNECTIVITY_FAILED = "Test connectivity failed"
MSG_QUERYING_CERT_INFO = "Querying certificate info for: {}"
MSG_QUERYING_IP_REP = "Checking IP reputation for: {}"
MSG_QUERYING_DOMAIN_REP = "Checking domain reputation for: {}"

# Error Messages
ERROR_UNEXPECTED_RESPONSE = "Unexpected response structure"
ERROR_NO_CERT_DATA = "No certificate data in response"
ERROR_NO_BLACKLIST_DATA = "No blacklist data in response"
