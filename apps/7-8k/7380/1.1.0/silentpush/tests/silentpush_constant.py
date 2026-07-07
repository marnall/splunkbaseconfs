# File: silentpush_constant.py
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

import encryption_helper


JSON_CONTENT_TYPE = "application/json"
DEFAULT_ASSET_ID = "20000"
DEFAULT_JSON_HEADERS = {"Content-Type": JSON_CONTENT_TYPE}
MISSING_REQUIRED_PARAMETER = {"message": "missing required parameter"}
FORM_URLENCODED = "application/x-www-form-urlencoded"
DEFAULT_FORM_URLENCODED_HEADERS = {"Content-Type": FORM_URLENCODED}
IMAGE_CONTENT_TYPE = "image/jpeg"
DEFAULT_IMAGE_HEADERS = {"Content-Type": IMAGE_CONTENT_TYPE}
DEFAULT_CSV_HEADERS = {"Content-Type": "binary/octet-stream"}

cipher_text = encryption_helper.encrypt("<dummy_api_token>", DEFAULT_ASSET_ID)

TEST_JSON = {
    "action": "<action name>",
    "identifier": "<action_name>",
    "asset_id": DEFAULT_ASSET_ID,
    "config": {
        "appname": "-",
        "directory": "silentpush_6bf6844d-f642-4f40-964c-87b917fec845",
        "main_module": "silentpush_connector.py",
        "base_url": "https://api.silentpush.com",
        "verify_server_cert": False,
        "api_key": cipher_text,
    },
    "debug_level": 3,
    "dec_key": DEFAULT_ASSET_ID,
    "parameters": [{}],
}
APIKEY_AUTH_CONFIG = {"X-API-KEY": cipher_text}

DUMMY_API_TOKEN = "<dummy_api_token>"  # NOSONAR

ABC_COM = "abc.com"  # NOSONAR
ABCD_COM = "abcd.com"  # NOSONAR
ABCDE_TK = "abcde.tk"  # NOSONAR
IPV6_EXAMPLE = "2a06:98c1:3121::2"  # NOSONAR
DATE_EXAMPLE = "2022-12-06 21:25:44"  # NOSONAR
AS_NAME = "BCD-AES, US"  # NOSONAR
FORWARD_LOOKUP_ANSWER = "vida.ns.cloudflare.com"  # NOSONAR
REGISTRAR = "ENOM, INC."  # NOSONAR
SUBNET = "20.192.0.0/10"  # NOSONAR
NS_SERVER = "a.dns-servers.net.ru"  # NOSONAR
CHAIN = "DigiCert Global G2 TLS RSA SHA256 2020 CA1"  # NOSONAR
MULTIPLE_DOMAINS = "abc.com , xyz.io, def.com, silentpush.com"  # NOSONAR
DEFAULT_DOMAIN = "www.silentpush.com"  # NOSONAR
DEFAULT_DOMAIN_WITHOUT_WWW = "silentpush.com"  # NOSONAR
INVALID_DROPDOWN_RESPONSE = "{'ok': True}"  # NOSONAR
SAMPLE_REGEX = "^sil[[:alpha:]]{3}\\.[a-z]{2,}$"  # NOSONAR
