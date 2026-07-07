#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
NAME = "name"
SPLUNK_HOME = "SPLUNK_HOME"
SPLUNK_DB = "SPLUNK_DB"
SPLUNK_TA_REMEDY = "Splunk_TA_remedy"
MODINPUTS = "modinputs"
APP_NAME = "Splunk_TA_remedy"
TICKET = "ticket"
SERVER_URI = "server_uri"
SESSION_KEY = "session_key"
CHECKPOINT_DIR = "checkpoint_dir"
AUTHENTICATION_INFO = "AuthenticationInfo"
ACTION = "Action"
INCIDENT_NUMBER = "Incident_Number"
FIELD_SEP = ","
LOGGING_STANZA = "logging"
LOG_LEVEL = "loglevel"
DEFAULT_LOG_LEVEL = "INFO"
# remedy conf
REMEDY_CONF = "splunk_ta_remedy_settings"
# remedy_account
REMEDY_ACCOUNT = "additional_parameters"
USER = "user"
PASSWORD = "password"
URL = "server_url"
SERVER_NAME = "server_name"
HTTP_SCHEME = "http_scheme"
DISABLE_SSL_CERTIFICATE_VALIDATION = "disable_ssl_certificate_validation"
CERTIFICATE_PATH = "ca_certs_path"
# remedy_ws
REMEDY_WS = "remedy_ws"
CREATE_WSDL_URL = "create_wsdl_url"
CREATE_WSDL_FILE_PATH = "create_wsdl_file_path"
CREATE_OPERATION_NAME = "create_operation_name"
MODIFY_WSDL_URL = "modify_wsdl_url"
MODIFY_WSDL_FILE_PATH = "modify_wsdl_file_path"
MODIFY_OPERATION_NAME = "modify_operation_name"
QUERY_WSDL_URL = "query_wsdl_url"
QUERY_WSDL_FILE_PATH = "query_wsdl_file_path"
QUERY_OPERATION_NAME = "query_operation_name"
# remedy fields conf
REMEDY_FIELDS_CONF = "remedy_fields"
CREATE_INCIDENT = "create_incident"
UPDATE_INCIDENT = "update_incident"
REQUIRED = "required"
# ignore fields
IGNORE_FIELDS = (REQUIRED, "appName", "userName", "disabled", "name")
# Urllib related constants
URLLIB_USERNAME = "username"
URLLIB_PASSWORD = "pwd"
URLLIB_PREFIX = '<?xml version="1.0"'
# Proxy related constants
PROXY_USERNAME = "proxy_username"
PROXY_PASSWORD = "proxy_password"
PROXY_TYPE = "proxy_type"
PROXY_URL = "proxy_url"
PROXY_PORT = "proxy_port"
PROXY_STANZA = "proxy"
PROXY_ENABLED = "proxy_enabled"
CHECKPOINT_COLLECTION_NAME = "Splunk_TA_remedy_input_checkpointer"
SOURCETYPE = {
    "incident": "remedy:incident",
    "audit": "remedy:audit",
    "incident_worklog": "remedy:incident:worklog",
}
SMART_IT_INSTANCE_ID_ENDPOINT = "/smartit/app/#/incidentPV/{}"
