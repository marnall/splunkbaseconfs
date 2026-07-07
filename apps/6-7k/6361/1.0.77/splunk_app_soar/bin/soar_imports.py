# Copyright (C) 2023-2024 Splunk Inc. All Rights Reserved.

APP_NAME = "splunk_app_soar"

# Endpoints
SOAR_CONF = f"/servicesNS/nobody/{APP_NAME}/configs/conf-soar"
INPUTS_CONF = f"/servicesNS/nobody/{APP_NAME}/configs/conf-inputs"
SOAR_PASSWORDS_CONF = f"/servicesNS/nobody/{APP_NAME}/storage/passwords"
SOAR_CONF_PROPS = f"/servicesNS/nobody/{APP_NAME}/properties/soar"
INPUTS_CONF_PROPS = f"/servicesNS/nobody/{APP_NAME}/properties/inputs"

GLOBAL_ACCOUNT = f"/servicesNS/nobody/{APP_NAME}/ta_splunk_app_soar_account"
INPUT_ENDPOINT = f"/servicesNS/nobody/{APP_NAME}/ta_splunk_app_soar_sas_audit"

# Phantom/SOAR REST endpoints
PHANTOM_VERIFY_SERVER_URL_USER_SETTINGS = (
    "{server}/rest/user_settings"
)

# Common messages:
REDIRECT_DETECTED_MSG = (
    "HTTP redirect has been detected and redirects are disabled for security reasons."
)
SERVER_MUST_BE_HTTPS_MSG = "Server must be https"
INVALID_SERVER_URL = "Invalid SOAR server URL"
INVALID_PROXY_URL = "Invalid proxy URL"
FAILED_TO_VERIFY_SERVER_MSG = "Failed to verify SOAR server"
