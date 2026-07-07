# File: silentpush_consts.py
#
# Copyright (c) 2024-2025 Splunk Inc.
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

# messages
EXECUTION_START_MESSAGE = "Executing {0} action"
TEST_CONNECTIVITY_START_MESSAGE = "Connecting to {0}"
SUCCESS_TEST_CONNECTIVITY = "Test Connectivity Passed"
SUCCESS_ON_POLL = "Poll executed successfully"
ERROR_TEST_CONNECTIVITY = "Test Connectivity Failed"
REQUEST_DEFAULT_TIMEOUT = 60
EXPORT_REQUEST_DEFAULT_TIMEOUT = 180

ACTION_LIST_IP_INFO_SUCCESS_RESPONSE = "Successfully fetched IPs' information"
ACTION_DOMAIN_INFRATAGS_SUCCESS_RESPONSE = "Successfully fetched domains' infratags"
ACTION_LIST_DOMAIN_INFO_SUCCESS_RESPONSE = "Successfully fetched domains' information"
ACTION_SEARCH_DOMAINS_SUCCESS_RESPONSE = "Successfully fetched domains"
ACTION_IPV4_REPUTATION_SUCCESS_RESPONSE = "Successfully fetched IPv4 reputation"
ACTION_ENRICHMENT_SUCCESS_RESPONSE = "Successfully fetched enrichment data"
ACTION_DOMAIN_CERTIFICATES_SUCCESS_RESPONSE = "Successfully fetched Domain certificates"
ACTION_ASN_TAKEDOWN_REPUTATION_SUCCESS_RESPONSE = "Successfully fetched ASN takedown reputation"
ACTION_ASN_REPUTATION_SUCCESS_RESPONSE = "Successfully fetched ASN reputation"
ACTION_GET_JOB_STATUS_SUCCESS_RESPONSE = "Successfully fetched job's information"
ACTION_NAMESERVER_REPUTATION_SUCCESS_RESPONSE = "Successfully fetched nameserver reputation"
ACTION_SUBNET_REPUTATION_SUCCESS_RESPONSE = "Successfully fetched subnet reputation"
ACTION_GET_ASNS_SEEN_FOR_DOMAIN_SUCCESS_RESPONSE = "Successfully fetched ASNs seen for the domain"
ACTION_LIVE_URL_SCAN_SUCCESS_RESPONSE = "Successfully scanned data from live URL"
ACTION_LIVE_URL_SCREENSHOT_SUCCESS_RESPONSE = "Successfully fetched screenshot from live URL"
ACTION_FORWARD_LOOKUP_SUCCESS_RESPONSE = "Successfully performed forward lookup"
ACTION_REVERSE_LOOKUP_SUCCESS_RESPONSE = "Successfully performed reverse lookup"
ACTION_DENSITY_LOOKUP_SUCCESS_RESPONSE = "Successfully performed density lookup"
ACTION_SEARCH_SCAN_DATA_SUCCESS_RESPONSE = "Successfully fetched scan data"
ACTION_FUTURE_ATTACK_FEED_SUCCESS_RESPONSE = "Successfully fetched future attack feed"
ACTION_GET_DATA_EXPORT_SUCCESS_RESPONSE = "Successfully downloaded feed data"

ERROR_INVALID_INT_PARAM = "Please provide a valid integer value in the '{key}' parameter"
ERROR_NEG_INT_PARAM = "Please provide a positive integer value in the '{key}' parameter"
ERROR_INVALID_PARAM = "Please provide a valid value in the '{key}' parameter"
ERROR_MESSAGE_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
EMPTY_RESPONSE_STATUS_CODES = [200, 204]
ERROR_INVALID_SELECTION = "Invalid '{0}' selected. Must be one of: {1}."
ERROR_GENERAL_MESSAGE = "Status code: {0}, Data from server: {1}"
ERROR_HTML_RESPONSE = "Error parsing html response"
ERROR_ZERO_INT_PARAM = "Please provide a non-zero integer value in the '{key}' parameter"
ERROR_INVALID_JSON_PARAM = "Please provide a valid JSON value for the '{key}' parameter"
ERROR_INVALID_LIST_PARAM = "Please provide a valid list value for the '{key}' parameter"
ERROR_INVALID_BOOL_PARAM = "Please provide a valid boolean value for the '{key}' parameter"
ERROR_MISSING_REQUIRED_PARAM = "'{key}' is required parameter"
INGESTION_START_MESSAGE = "Ingesting the data"
CONTAINER_ERROR_MESSAGE = "Error occurred while saving the container: ID {}: {}"
ARTIFACT_ERROR_MESSAGE = "Error occurred while saving the artifact(s): {}"
MAX_RETRIES = 3
MAX_LIMIT_VALUE = 10000


# endpoints
BASE_URL = "https://api.silentpush.com"
TEST_CONNECTIVITY_ENDPOINT = "/api/v1/merge-api/explore/domain/whois/silentpush.com"
LIST_DOMAIN_INFORMATION_ENDPOINT = "/api/v1/merge-api/explore/bulk/domaininfo"
LIST_DOMAIN_ENDPOINT_RISK_SCORE_ENDPOINT = "/api/v1/merge-api/explore/bulk/domain/riskscore"
LIST_DOMAIN_ENDPOINT_WHOIS_INFO_ENDPOINT = "/api/v1/merge-api/explore/domain/whoislive/{}"
GET_DOMAIN_CERTIFICATES_ENDPOINT = "/api/v1/merge-api/explore/domain/certificates/{{domain}}"
DOMAIN_SEARCH_ENDPOINT = "/api/v1/merge-api/explore/domain/search"
LIST_DOMAIN_INFRATAGS_ENDPOINT = "/api/v1/merge-api/explore/bulk/domain/infratags"
GET_ENRICHMENT_DATA_ENDPOINT = "/api/v1/merge-api/explore/enrich/{{resource}}/{{value}}"
LIST_IP_INFORMATION_ENDPOINT = "/api/v1/merge-api/explore/bulk/ip2asn/{{resource}}"
GET_ASN_REPUTATION_ENDPOINT = "/api/v1/merge-api/explore/ipreputation/history/asn/{{asn}}"
GET_ASN_TAKEDOWN_REPUTATION_ENDPOINT = "/api/v1/merge-api/explore/takedownreputation/history/asn/{{asn}}"
GET_IPV4_REPUTATION_ENDPOINT = "/api/v1/merge-api/explore/ipreputation/history/ipv4/{{ipv4}}"
GET_JOB_STATUS_ENDPOINT = "/api/v1/merge-api/explore/job/{{job_id}}"
GET_JOB_STATUS_RESULT_TYPE_OPTIONS = {"status": "status_only", "include metadata": "force_metadata_on", "exclude metadata": "force_metadata_off"}
GET_NAMESERVER_REPUTATION_ENDPOINT = "/api/v1/merge-api/explore/nsreputation/history/nameserver/{{nameserver}}"
GET_SUBNET_REPUTATION_ENDPOINT = "/api/v1/merge-api/explore/ipreputation/history/subnet/{{subnet}}"
GET_ASNS_SEEN_FOR_DOMAIN_ENDPOINT = "/api/v1/merge-api/explore/padns/lookup/domain/asns/{{domain}}"
FORWARD_PADNS_LOOKUP_ENDPOINT = "/api/v1/merge-api/explore/padns/lookup/query/{{qtype}}/{{qname}}"
REVERSE_PADNS_LOOKUP_ENDPOINT = "/api/v1/merge-api/explore/padns/lookup/answer/{{qtype}}/{{qname}}"
DENSITY_LOOKUP_ENDPOINT = "/api/v1/merge-api/explore/padns/lookup/density/{{qtype}}/{{query}}"
LIVE_URL_SCAN_ENDPOINT = "/api/v1/merge-api/explore/tools/scanondemand"
LIVE_URL_SCREENSHOT_ENDPOINT = "/api/v1/merge-api/explore/tools/screenshotondemand"
SEARCH_SCAN_DATA_ENDPOINT = "/api/v1/merge-api/explore/scandata/search/raw"
GET_FUTURE_ATTACK_FEED_ENDPOINT = "/api/v2/iocs/threat-ranking/"

DOMAIN_CERTIFICATES_PREFER_OPTIONS = {"result": "result", "job id": "job_id"}
ENRICHMENT_DATA_RESOURCE_OPTIONS = {"domain": "domain", "ipv4": "ipv4", "ipv6": "ipv6"}
LIST_DOMAIN_INFRATAGS_MODE_OPTIONS = {"live": "live", "padns": "padns"}
LIST_DOMAIN_INFRATAGS_MATCH_OPTIONS = {"self": "self", "full": "full"}
PADNS_LOOKUP_MATCH_OPTIONS = {"strict": "strict", "self": "self"}
PADNS_LOOKUP_OUTPUT_FORMAT_OPTIONS = {"padns": "padns", "cof": "cof"}
PADNS_LOOKUP_PREFER_OPTIONS = {"result": "result", "job id": "job_id"}
DENSITY_LOOKUP_QTYPE_OPTIONS = {
    "nssrv": "nssrv",
    "mxsrv": "mxsrv",
    "nshash": "nshash",
    "mxhash": "mxhash",
    "ipv4": "ipv4",
    "ipv6": "ipv6",
    "asn": "asn",
    "chv": "chv",
}
DENSITY_LOOKUP_SCOPE_OPTIONS = {
    "ip": "ip",
    "subnet": "subnet",
    "subnet ips": "subnet_ips",
    "asn": "asn",
    "asn subnets": "asn_subnets",
    "host": "host",
    "domain": "domain",
    "subdomain": "subdomain",
    "chv": "chv",
    "chv analysis": "chv_analysis",
}
LIVE_URL_SCAN_PLATFORM_OPTIONS = {
    "desktop": "Desktop",
    "mobile": "Mobile",
    "crawler": "Crawler",
}
LIVE_URL_SCAN_OS_OPTIONS = {
    "windows": "Windows",
    "linux": "Linux",
    "macos": "MacOS",
    "ios": "iOS",
    "android": "Android",
}
LIVE_URL_SCAN_BROWSER_OPTIONS = {
    "firefox": "Firefox",
    "chrome": "Chrome",
    "edge": "Edge",
    "safari": "Safari",
}
LIVE_URL_SCAN_REGION_OPTIONS = {"us": "US", "eu": "EU", "as": "AS", "tor": "TOR"}
FORWARD_PADNS_LOOKUP_QTYPE_OPTIONS = {
    "a": "a",
    "aaaa": "aaaa",
    "cname": "cname",
    "mx": "mx",
    "ns": "ns",
    "ptr4": "ptr4",
    "ptr6": "ptr6",
    "any": "any",
    "soa": "soa",
    "txt": "txt",
    "anyipv4": "anyipv4",
    "anyipv6": "anyipv6",
}
REVERSE_PADNS_LOOKUP_QTYPE_OPTIONS = {
    "a": "a",
    "aaaa": "aaaa",
    "cname": "cname",
    "mx": "mx",
    "ns": "ns",
    "ptr4": "ptr4",
    "ptr6": "ptr6",
    "soa": "soa",
    "txt": "txt",
    "mxhash": "mxhash",
    "nshash": "nshash",
    "soahash": "soahash",
    "txthash": "txthash",
}
