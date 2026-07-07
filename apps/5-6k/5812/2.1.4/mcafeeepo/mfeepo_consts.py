# File: mfeepo_consts.py
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

EPO_JSON_USERNAME = "username"
EPO_JSON_PASSWORD = "password"  # pragma: allowlist secret
EPO_JSON_HOST = "ip_hostname"
EPO_JSON_PORT = "port"
EPO_JSON_QTAG = "quarantine_tag"
EPO_JSON_TAG = "tag"
EPO_JSON_WAKEUP_AGENT = "wakeup_agent"

KEY_TAGS = "EPOLeafNode.Tags"
KEY_ETAGS = "EPOLeafNode.ExludedTags"
IP_ADDR = "EPOComputerProperties.IPAddress"
NAME = "EPOComputerProperties.ComputerName"
ERROR_MESSAGE_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
