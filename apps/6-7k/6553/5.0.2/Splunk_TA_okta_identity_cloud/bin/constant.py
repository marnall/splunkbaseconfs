##
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

DATE_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
DEFAULT_FALLBACK_DATE = "1970-01-01T00:00:00.000Z"
QUERY_WINDOW_SIZE = 3600
MAX_USER_LIMIT = "200"
MAX_APP_LIMIT = "200"
MAX_GROUP_LIMIT = "10000"
ACCOUNT_CONFIG_FILE = "splunk_ta_okta_identity_cloud_account"
SETTINGS_CONFIG_FILE = "splunk_ta_okta_identity_cloud_settings"
MODULAR_INPUT_NAME = "okta_identity_cloud://{}"
REQTIMEOUT = float(90)
METRIC_URL = "https://{account_domain}/api/v1/{metric}"
TOKEN_URL = "https://{account_domain}/oauth2/v1/token"
DEFAULT_SCOPE = (
    "offline_access okta.logs.read okta.users.read okta.groups.read okta.apps.read"
)
AUTH_TYPE_BASIC = "basic"
AUTH_TYPE_OAUTH_CLIENT = "oauth_client_credentials"
AUTH_TYPE_OAUTH_AUTHZ = "oauth"
OAUTH_TYPES = {AUTH_TYPE_OAUTH_AUTHZ, AUTH_TYPE_OAUTH_CLIENT}

APP_NAME = "Splunk_TA_okta_identity_cloud"
OAUTH_ENDPOINT = "Splunk_TA_okta_identity_cloud_oauth"
TOKEN_ENDPOINT = "/oauth2/v1/token"

CONNECTION_ERROR = "log_connection_error"
CONFIGURATION_ERROR = "log_configuration_error"
PERMISSION_ERROR = "log_permission_error"
AUTHENTICATION_ERROR = "log_authentication_error"
SERVER_ERROR = "log_server_error"
GENERAL_EXCEPTION = "log_exception"
OKTA_IDENTITY_CLOUD_ERROR = "okta_identity_cloud_ta_error"
UCC_EXECPTION_EXE_LABEL = "splunk_ta_okta_identity_cloud_exception_{}"
