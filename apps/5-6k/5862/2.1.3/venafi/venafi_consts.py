# File: venafi_consts.py
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

# state file keys
VENAFI_STATE_ACCESS_TOKEN = "access_token"
VENAFI_STATE_REFRESH_TOKEN = "refresh_token"
VENAFI_STATE_EXPIRES = "expires"
VENAFI_STATE_IS_ENCRYPTED = "is_encrypted"

# APIs
VENAFI_FETCH_ACCESS_TOKEN_URI = "/vedauth/Authorize/Token"
VENAFI_FETCH_TOKEN_URI = "/vedauth/authorize/oauth"
VENAFI_LIST_CERTIFICATES_URI = "/vedsdk/certificates"
VENAFI_RENEW_CERTIFICATE_URI = "/vedsdk/Certificates/Renew"
VENAFI_VERIFY_TOKEN_URI = "/vedauth/Authorize/Verify"
VENAFI_CREATE_CERTIFICATE_URI = "/vedsdk/Certificates/Request"
VENAFI_LIST_POLICIES_URI = "/vedsdk/Config/FindObjectsOfClass"
VENAFI_REVOKE_CERTIFICATE_URI = "/vedsdk/Certificates/Revoke"
VENAFI_GET_CERTIFICATE_URI = "/vedsdk/Certificates/Retrieve"

# messages
TEST_CONNECTIVITY_FAILED = "Test Connectivity Failed"
TEST_CONNECTIVITY_SUCCESS = "Test Connectivity Passed"
VENAFI_VALID_INTEGER_MESSAGE = "Please provide a valid integer value in the {param}"
VENAFI_NON_NEGATIVE_INTEGER_MESSAGE = "Please provide a valid non-negative integer value in the {param}"
VENAFI_POSITIVE_INTEGER_MESSAGE = "Please provide a valid non-zero positive integer value in the {param}"
VENAFI_ENCRYPTION_ERROR = "Error occurred while encrypting the state file"
VENAFI_DECRYPTION_ERROR = "Error occurred while decrypting the state file"
VENAFI_ERROR_MESSAGE_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
VENAFI_INVALID_REFRESH_TOKEN = "refresh token is invalid"

VENAFI_DEFAULT_TIMEOUT = 30
VENAFI_LIST_CERTIFICATES_PARAMS = {
    "country": "C",
    "common_name": "CN",
    "key_algorithm": "KeyAlgorithm",
    "key_size": "KeySize",
    "key_size_greater": "KeySizeGreater",
    "key_size_less": "KeySizeLess",
    "city": "L",
    "organization": "O",
    "organization_unit": "OU",
    "state": "S",
    "san_dns": "SAN-DNS",
    "san_email": "SAN-Email",
    "san_ip": "SAN-IP",
    "san_upn": "SAN-UPN",
    "san_uri": "SAN-URI",
    "serial": "Serial",
    "signature_algorithm": "SignatureAlgorithm",
    "thumbprint": "Thumbprint",
    "valid_from": "ValidFrom",
    "valid_to": "ValidTo",
    "valid_to_greater": "ValidToGreater",
    "valid_to_less": "ValidToLess",
}
VENAFI_GET_CERTIFICATE_PARAMS = {
    "certificate_dn": "CertificateDN",
    "friendly_name": "FriendlyName",
    "keystore_password": "KeystorePassword",  # pragma: allowlist secret
    "password": "Password",  # pragma: allowlist secret
}
