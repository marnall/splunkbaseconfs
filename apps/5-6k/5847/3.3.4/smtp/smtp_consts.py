# File: smtp_consts.py
#
# Copyright (c) 2016-2026 Splunk Inc.
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
SMTP_SUCC_SMTP_CONNECTIVITY_TO_SERVER = "Connected to server"
SMTP_SUCC_SMTP_EMAIL_SENT = "Email sent"
SMTP_ERROR_SMTP_CONNECTIVITY_TO_SERVER = "Connection to server failed"
SMTP_ERROR_SMTP_SEND_EMAIL = "Email send failed"
SMTP_SUCC_CONNECTIVITY_TEST = "Test Connectivity Passed for {} authentication"
SMTP_ERROR_CONNECTIVITY_TEST = "Test Connectivity Failed for {} authentication"
SMTP_FAILED_CONNECTIVITY_TEST = " Please run test connectivity first."

SMTP_PROG_UNABLE_TO_ATTACH_FILE = "Unable to attach file {}"
SMTP_MESSAGE_SKIP_AUTH_NO_USERNAME_PASSWORD = "Skipping authentication, since Username or Password not configured"  # pragma: allowlist secret
SMTP_ERROR_PARSE_HEADERS = "Unable to parse headers as a dictionary: {}"
SMTP_UNICODE_ERROR_MESSAGE = "Error occurred while associating the email content in the email message object. \
If you are dealing with the Unicode characters,please mark the asset configuration parameter 'Enable Unicode \
support' as true, if not done already and try again."
SMTP_JSON_ATTACHMENTS = "attachments"
SMTP_JSON_BODY = "body"
SMTP_JSON_HEADERS = "headers"
SMTP_JSON_FROM = "from"
SMTP_JSON_PORT = "port"
SMTP_JSON_SUBJECT = "subject"
SMTP_JSON_TO = "to"
SMTP_JSON_CC = "cc"
SMTP_JSON_BCC = "bcc"
SMTP_JSON_USE_SSL = "use_ssl"
SMTP_JSON_TOTAL_SCANS = "total_scans"
SMTP_JSON_TOTAL_POSITIVES = "total_positives"
SMTP_JSON_TOTAL_GUESTS = "total_guests"
SMTP_JSON_TOTAL_GUESTS_RUNNING = "total_guests_running"
SMTP_JSON_SSL_CONFIG = "ssl_config"
SSL_CONFIG_NONE = "None"
SSL_CONFIG_SSL = "SSL"
SSL_CONFIG_STARTTLS = "StartTLS"
SMTP_ENCODING = "encoding"
SMTP_ALLOW_SMTPUTF8 = "allow_smtputf8"
SMTP_PASSWORD_LESS_AUTH_TYPE = "Passwordless"  # pragma: allowlist secret
SMTP_OAUTH_AUTH_TYPE = "OAuth"
SMTP_BASIC_AUTH_TYPE = "Basic"
SMTP_AUTOMATIC_AUTH_TYPE = "Automatic"
SMTP_TEST_CONNECTIVITY = "Test Connectivity"

SMTP_SENDING_TEST_MAIL = "Sending test mail"
SMTP_DONE = "Done..."

SMTP_ERROR_SSL_CONFIG_SSL = "Possible misconfiguration. \
The current SSL configuration value requires the server to speak SSL from the beginning of the connection."
SMTP_ERROR_STARTTLS_CONFIG = "Possible misconfiguration. \
The current SSL configuration value requires the server to support the startTLS command issued after a connection is made."
SMTP_ERROR_SMTPUTF8_CONFIG = "Unable to encode the Unicode characters. Possible misconfiguration. \
Either the server does not support SMTPUT8 or the 'Enable SMTPUTF8 support' asset configuration parameter is set to False"
SMTP_ERROR_TO_FROM_UNAVAILABLE = "Error: Failed to send the email. The {} is unavailable. Please check the action parameters"
SMTP_ERROR_CONNECTIVITY_TO_SERVER = "Error connecting to server"
SMTP_ERROR_LOGGING_IN_TO_SERVER = "Error logging in to server"
SMTP_REQUIRED_PARAM_AUTH = (
    "One or more required parameters for {} authentication is missing. The required parameters for {} authentication are: {}"
)
SMTP_STATE_FILE_CORRUPT_ERROR = (
    "Error occurred while loading the state file due to its unexpected format. "
    "Resetting the state file with the default format. Please try again."
)

SMTP_ASSET_CORRUPTED = (
    "ERROR: The token present in the state file is corrupted. Deleting the token. Please test the connectivity to generate a new token"
)

# Constants relating to '_get_error_message_from_exception'
ERROR_MESSAGE_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
TYPE_ERROR_MESSAGE = "Error occurred while connecting to the server. Please check the asset configuration and|or the action parameters"
PARSE_ERROR_MESSAGE = "Unable to parse the error message. Please check the asset configuration and|or action parameters"

DEFAULT_REQUEST_TIMEOUT = 30  # 30 seconds


SMTP_STATE_IS_ENCRYPTED = "is_encrypted"

# For encryption and decryption
SMTP_ENCRYPT_TOKEN = "Encrypting the {} token"
SMTP_DECRYPT_TOKEN = "Decrypting the {} token"
SMTP_ENCRYPTION_ERROR = "Error occurred while encrypting the state file"
SMTP_DECRYPTION_ERROR = "Error occurred while decrypting the state file"


SMTP_VALID_INT_MESSAGE = "Please provide a valid integer value in the '{param}'"
SMTP_NON_NEG_INT_MESSAGE = "Please provide a valid non-negative integer value in the '{param}'"
SMTP_NON_NEG_NON_ZERO_INT_MESSAGE = "Please provide a valid non-zero positive integer value in '{param}'"
SMTP_AUTH_MESSAGE = "Using {} Authentication"
SMTP_AUTH_FAILED_ACTION_MESSAGE = "{} failed for {} authentication. {}"
SMTP_ALLOWED_AUTH_TYPES = ["Automatic", "OAuth", "Basic", "Passwordless"]
BLEACH_SAFE_HTML_ATTRIBUTES = {
    "*": ["id", "class", "lang", "style", "title", "width", "height", "name", "placeholder", "required", "value"],
    "table": [
        "summary",
        "align",
        "frame",
        "rules",
        "border",
        "bgcolor",
        "cellspacing",
        "cellpadding",
    ],
    "col": [
        "span",
        "align",
        "valign",
    ],
    "colgroup": [
        "span",
        "align",
        "valign",
    ],
    "thead": [
        "align",
        "valign",
    ],
    "tbody": [
        "align",
        "valign",
    ],
    "tfoot": [
        "align",
        "valign",
    ],
    "tr": [
        "align",
        "valign",
        "bgcolor",
    ],
    "th": [
        "headers",
        "scope",
        "abbr",
        "axis",
        "rowspan",
        "colspan",
        "nowrap",
        "align",
        "valign",
        "bgcolor",
    ],
    "td": [
        "headers",
        "scope",
        "abbr",
        "axis",
        "rowspan",
        "colspan",
        "nowrap",
        "align",
        "valign",
        "bgcolor",
    ],
    "img": [
        "src",
        "ismap",
        "loading",
        "longdesc",
        "alt",
        "referrerpolicy",
        "srcset",
        "usemapsizes",
        "align",
        "border",
        "hspace",
        "vspace",
    ],
    "a": ["href", "alt", "download", "hreflang", "media", "referrerpolicy", "rel", "target", "type"],
    "area": ["alt", "coords", "download", "href", "hreflang", "media", "referrerpolicy", "rel", "shape", "target", "type"],
    "textarea": ["rows", "cols", "disabled", "autofocus", "form", "maxlength", "readonly", "wrap"],
    "input": [
        "type",
        "accept",
        "alt",
        "autocomplete",
        "autofocus",
        "checked",
        "dirname",
        "disabled",
        "form",
        "formaction",
        "formenctype",
        "formmethod",
        "formnovalidate",
        "formtarget",
        "type",
        "list",
        "max",
        "maxlength",
        "min",
        "minlength",
        "multiple",
        "pattern",
        "readonly",
        "size",
        "src",
        "step",
    ],
    "button": ["autofocus", "disabled", "form", "formaction", "formenctype", "formmethod", "formnovalidate", "formtarget", "type"],
    "bdo": ["dir"],
    "optgroup": ["disable", "label"],
    "meter": ["form", "high", "low", "max", "min", "optimum"],
    "base": ["href", "target"],
    "del": ["cite", "datetime"],
    "details": ["open"],
    "dialog": ["open"],
    "fieldset": ["disabled", "form"],
    "form": ["accept-charset", "action", "autocomplete", "enctype", "method", "novalidate", "rel", "target"],
    "ins": ["cite", "datetime"],
    "label": ["for", "form"],
    "ol": ["reversed", "start", "type"],
    "outgroup": ["disabled", "label"],
    "option": ["disabled", "label", "selected"],
    "output": ["for", "form"],
    "progress": ["max"],
    "q": ["cite"],
    "select": ["autofocus", "disabled", "form", "multiple", "size"],
    "source": ["media", "sizes", "src", "srcset", "type"],
    "style": ["media", "type"],
}
SMTP_BLEACH_ALLOWED_PROTOCOLS = ["cid", "data", "tel", "sms", "geo", "webcal", "callto"]
