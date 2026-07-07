# File: hyasinsight_consts.py
#
# Copyright (c) HYAS, 2022-2025
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
# Indicator Types
DOMAIN = "domain"
IP = "ip"
IPV4 = "ipv4"
EMAIL = "email"
PHONE = "phone"
IPV6 = "ipv6"
SHA256 = "sha256"
HASH = "hash"

# Endpoints
HYAS_BASE_URL = "https://apps.hyas.com/api/ext/"
PASSIVEDNS = "passivedns"
DYNAMICDNS = "dynamicdns"
PASSIVEHASH = "passivehash"
SINKHOLE = "sinkhole"
C2ATTRIBUTION = "c2attribution"
DEVICEGEO = "device_geo"
SSL = "ssl_certificate"
WHOIS = "whois"
SAMPLE = "sample"
SAMPLE_INFORMATION = "sample/information"
OS_INDICATOR = "os_indicators"
CURRENT_WHOIS_BASE_URL = "https://api.hyas.com"
CURRENT_WHOIS = "/whois/v1"
CURRENT_WHOIS_NAME = "current_whois"
SSL_CERTS = "ssl_certs"
ITEMS = "items"
SCAN_RESULT = "scan_results"
SAMPLE_INFORMATION_NAME = "sampleinfo"

# test Endpoints
HYAS_TEST_PASSIVEHASH_ENDPOINT = "passivehash"
HYAS_TEST_PAYLOAD_KEY = "domain"
HYAS_TEST_PAYLOAD_VALUE = "google.com"

# Request Data
HYAS_JSON_APIKEY = "apikey"  # pragma: allowlist secret
HYAS_JSON_APIKEY_HEADER = "x-api-key"  # pragma: allowlist secret

# regex
IP_REG = (
    r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.)"
    "{3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])$"
)
IPV6_REG = (
    r"(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,"
    r"7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,"
    r"4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,"
    r"4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,"
    r"3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,"
    r"2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,"
    r"4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,"
    r"4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|("
    r"2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,"
    r"1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2["
    r"0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,"
    r"1}[0-9]){0,1}[0-9]))"
)

DOMAIN_REG = (
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-_]{0,"
    r"61}[A-Za-z0-9])?\.)+["
    r"A-Za-z0-9][A-Za-z0-9-_]{0,61}[A-Za-z]$"
)

EMAIL_REG = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}"
PHONE_REG = r"^\+?[1-9]\d{1,14}$"
SHA_REG = "[A-Fa-f0-9]{64}"
URL_REG = (
    r"((http|https)://)(www.)?[a-zA-Z0-9@:%._\\+~#?&//=]{2,256}"
    "\\.[a-z]{2,6}\\b([-a-zA-Z0-9@:%._\\+~#?&//=]*)"
)
MD5_REG = r"(^[a-fA-F0-9]{32}$)"
SHA1_REG = r"\b[0-9a-fA-F]{40}\b"
SHA512_REG = r"\b[0-9a-fA-F]{128}\b"
IOC_NAME = {
    "ip": {"ipv4": IP_REG, "ipv6": IPV6_REG},
    "ipv4": IP_REG,
    "ipv6": IPV6_REG,
    "domain": DOMAIN_REG,
    "email": EMAIL_REG,
    "phone": PHONE_REG,
    "hash": {"sha256": SHA_REG, "md5": MD5_REG, "sha1": SHA1_REG, "sha512": SHA512_REG},
}

# status messages
HYAS_ERROR_MESSAGE_INVALID_INDICATOR_VALUE = "Invalid Indicator value"
HYAS_INVALID_APIKEY_ERROR = "Please provide a valid api key"  # pragma: allowlist secret
HYAS_TEST_CONN_PASSED = "Test Connectivity Passed"
HYAS_TEST_CONN_FAILED = "Test Connectivity Failed."

HYAS_ERROR_ASSET_API_KEY_ = "API Key asset setting not configured! Please validate asset configuration and save"  # pragma: allowlist secret
HYAS_ERROR_CODE_MESSAGE = "Error code unavailable"
HYAS_ERROR_MESSAGE_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
HYAS_PARSE_ERROR_MESSAGE = "Unable to parse the error message. Please check the asset configuration and|or action parameters"
HYAS_HTML_ERROR_MESSAGE = "Please check the asset configuration and|or action parameters"
HYAS_ASSET_ERROR_MESSAGE = "Please check the asset configuration and|or action parameters"
MALWARE_RECORD_MD5 = "Invalid indicator value. malware record accept only md5 hash"
C2_HASH_ERROR_MESSAGE = "Invalid indicator value. C2 attribution accept only sha256"

# Jsons used in params, result, summary etc.
ACTION_ID_PARAM = {
    "lookup_c2_domain": "domain",
    "lookup__c2__email": "email",
    "lookup_c2_ip": "ip",
    "lookup_c2_sha256": "sha256",
    "lookup_whois_domain": "domain",
    "lookup_device_geo_ipv4": "ipv4",
    "lookup_device_geo_ipv6": "ipv6",
    "lookup_whois_email": "email",
    "lookup_whois_phone": "phone",
    "lookup_dynamicdns_email": "email",
    "lookup_dynamicdns_ip": "ip",
    "lookup_sinkhole_ip": "ip",
    "lookup_passivehash_ip": "ip",
    "lookup_passivehash_domain": "domain",
    "lookup_passivedns_ip": "ip",
    "lookup_passivedns_domain": "domain",
    "lookup_ssl_certificate_ip": "ip",
    "lookup_current_whois_domain": "domain",
}

IOC_DETAILS = {
    "lookup_c2_domain": {"endpoint": C2ATTRIBUTION, "indicator_type": DOMAIN},
    "lookup__c2__email": {"endpoint": C2ATTRIBUTION, "indicator_type": EMAIL},
    "lookup_c2_ip": {"endpoint": C2ATTRIBUTION, "indicator_type": IP},
    "lookup_c2_sha256": {"endpoint": C2ATTRIBUTION, "indicator_type": SHA256},
    "lookup_whois_domain": {"endpoint": WHOIS, "indicator_type": DOMAIN},
    "lookup_whois_email": {"endpoint": WHOIS, "indicator_type": EMAIL},
    "lookup_whois_phone": {"endpoint": WHOIS, "indicator_type": PHONE},
    "lookup_device_geo_ipv4": {"endpoint": DEVICEGEO, "indicator_type": IPV4},
    "lookup_device_geo_ipv6": {"endpoint": DEVICEGEO, "indicator_type": IPV6},
    "lookup_dynamicdns_email": {"endpoint": DYNAMICDNS, "indicator_type": EMAIL},
    "lookup_dynamicdns_ip": {"endpoint": DYNAMICDNS, "indicator_type": IP},
    "lookup_sinkhole_ip": {"endpoint": SINKHOLE, "indicator_type": IPV4},
    "lookup_passivehash_ip": {"endpoint": PASSIVEHASH, "indicator_type": IPV4},
    "lookup_passivehash_domain": {"endpoint": PASSIVEHASH, "indicator_type": DOMAIN},
    "lookup_passivedns_domain": {"endpoint": PASSIVEDNS, "indicator_type": DOMAIN},
    "lookup_passivedns_ip": {"endpoint": PASSIVEDNS, "indicator_type": IPV4},
    "lookup_ssl_certificate_ip": {"endpoint": SSL, "indicator_type": IP},
    "lookup_current_whois_domain": {"endpoint": CURRENT_WHOIS, "indicator_type": DOMAIN},
}

ACTION_ID = [
    "lookup_c2_domain",
    "lookup__c2__email",
    "lookup_c2_ip",
    "lookup_c2_sha256",
    "lookup_whois_domain",
    "lookup_device_geo_ipv4",
    "lookup_device_geo_ipv6",
    "lookup_whois_email",
    "lookup_whois_phone",
    "lookup_dynamicdns_email",
    "lookup_dynamicdns_ip",
    "lookup_sinkhole_ip",
    "lookup_passivehash_ip",
    "lookup_passivehash_domain",
    "lookup_passivedns_ip",
    "lookup_passivedns_domain",
    "lookup_ssl_certificate_ip",
    "lookup_current_whois_domain",
]

DEFAULT_REQUEST_TIMEOUT = 600  # in seconds

PASSIVE_IOC = {"ipv4_regex": "ipv4", "domain_regex": "domain"}
DYNAMIC_IOC = {"ipv4_regex": "ip", "ipv6_regex": "ip", "email_regex": "email", "domain_regex": "domain"}
PASSIVEHASH_IOC = {"ipv4_regex": "ipv4", "domain_regex": "domain"}
C2ATTRIBUTION_IOC = {"ipv4_regex": "ip", "ipv6_regex": "ip", "email_regex": "email", "domain_regex": "domain", "sha256_regex": "sha256"}
WHOIS_IOC = {"phone_regex": "phone", "email_regex": "email", "domain_regex": "domain"}
WHOIS_CURRENT_NAMES = {"domain_regex": "domain"}
SINKHOLE_IOC = {"ipv4_regex": "ipv4"}
SSL_IOC = {"ipv4_regex": "ip", "ipv6_regex": "ip", "sha1_regex": "hash", "domain_regex": "domain"}
DEVICE_IOC = {"ipv4_regex": "ipv4", "ipv6_regex": "ipv6"}
SAMPLE_INFORMATION_IOC = {"md5_regex": "hash", "sha256_regex": "hash", "sha1_regex": "hash", "sha512_regex": "hash"}
SAMPLE_IOC = {"md5_regex": "md5", "domain_regex": "domain", "ipv4_regex": "ipv4"}
OS_INDICATOR_IOC = {
    "md5_regex": "md5",
    "sha256_regex": "sha256",
    "sha1_regex": "sha1",
    "domain_regex": "domain",
    "ipv4_regex": "ipv4",
    "ipv6_regex": "ipv6",
}
