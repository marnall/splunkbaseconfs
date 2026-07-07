# File: metadefender_consts.py
#
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
DEFAULT_TIMEOUT = 30

METADEFENDER_API_BASE_URL = "https://api.metadefender.com/"
METADEFENDER_API_FILE_REPUTATION = "v4/hash/{file}"
METADEFENDER_API_ADDITIONAL_INFO = "v4/hash/{file}/{additional_info_key}"
METADEFENDER_API_IP_REPUTATION = "v4/ip/{ip}"
METADEFENDER_JSON_HASH = "hash"
METADEFENDER_JSON_HASH_METADATA = "metadata"
METADEFENDER_JSON_IP = "ip"
METADEFENDER_JSON_ADDITIONAL_INFO = "additional_info"
METADEFENDER_CONFIG_API_KEY = "api_key"  # pragma: allowlist secret
