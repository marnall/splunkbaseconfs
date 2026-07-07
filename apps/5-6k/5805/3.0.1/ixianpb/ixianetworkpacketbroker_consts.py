# File: ixianetworkpacketbroker_consts.py
#
# Copyright (c) 2019-2025 Splunk Inc.
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
IXIA_GET_FILTERS_ENDPOINT = "/api/filters"
IXIA_GET_USERS_ENDPOINT = "/api/users"
IXIA_RESTART_ENDPOINT = "/api/actions/restart"
TOKEN_URL = "/api/actions/get_login_info"
MODE_MAP = {
    "Pass All": "PASS_ALL",
    "Pass By Criteria": "PASS_BY_CRITERIA",
    "PBC Unmatched": "PBC_UNMATCHED",
    "Disable": "DISABLE",
    "Deny By Criteria": "DENY_BY_CRITERIA",
    "DBC Matched": "DBC_MATCHED",
}
IP_TYPE_MAP = {
    "Source": ["ipv4_src", "source_ip"],
    "Destination": ["ipv4_dst", "destination_ip"],
    "Source or Destination": ["ipv4_src_or_dst", "source_or_destination_ip"],
    "Unidirectional Flow": ["ipv4_flow", "UNI"],
    "Bidirectional Flow": ["ipv4_flow", "BIDI"],
}
MAC_TYPE_MAP = {
    "Source": ["mac_src", "source_mac"],
    "Destination": ["mac_dst", "destination_mac"],
    "Source or Destination": ["mac_src_or_dst", "source_or_destination_mac"],
    "Unidirectional Flow": ["mac_flow", "UNI"],
    "Bidirectional Flow": ["mac_flow", "BIDI"],
}
PORT_TYPE_MAP = {
    "Source": ["layer4_src_port", "source_port"],
    "Destination": ["layer4_dst_port", "destination_port"],
    "Source or Destination": ["layer4_src_or_dst_port", "source_or_destination_port"],
    "Unidirectional Flow": ["layer4_port_flow", "UNI"],
    "Bidirectional Flow": ["layer4_port_flow", "BIDI"],
}
