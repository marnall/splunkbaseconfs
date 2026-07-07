"""File with constants used in integration."""

DATAMINR_BASE_URL = "https://gateway.dataminr.com/"
DATAMINR_AUTH_ENDPOINT = "auth/2/token"
DATAMINR_BASE_URL_V4 = "https://api.dataminr.com/"
DATAMINR_AUTH_ENDPOINT_V4 = "auth/v1/token"
HEADER_AUTH_PREFIX = "Dmauth"
HEADER_AUTH_PREFIX_V4 = "Bearer"
GRANT_TYPE = "api_key"
VERIFY_SSL = True
REQUEST_TIMEOUT = 120
ALL_ALERT_TYPES = ["alert", "flash", "urgent"]
NOT_SUPPORTED_WATCHLIST_TYPES = ["CUSTOM"]
APPLICATION_TYPE = "splunk_siem"
SPLUNK_CLOUD_HEC_PORT = 443
INTEGRATION_VERSION = "3.1.0"
