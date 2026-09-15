### GLOBAL CONFIGS ###
ADDON_NAME = "TA-scaleway_addon"
ADDON_VERSION = "1.0.0"

USER_AGENT = f"Scaleway-Addon-for-Splunk/{ADDON_VERSION}"

CONF_FILE_BASE_NAME = f"{ADDON_NAME.lower()}"
ACCOUNT_CONF_FILE_NAME = f"{CONF_FILE_BASE_NAME}_account"
SETTINGS_CONF_FILE_NAME = f"{CONF_FILE_BASE_NAME}_settings"

COLLECTION_NAME = f"{ADDON_NAME.replace('-', '_')}_checkpoint_lookup"
DEFAULT_CHECKPOINT_TIME = "00:00:00.000000"

API_BASE_URL = "https://api.scaleway.com"
API_CALL_MAX_RETRIES = 5
API_CALL_TIMEOUT_IN_SECONDS = 60
API_CALL_DELAY_WINDOW_IN_SECONDS = 50
API_CALL_RETRY_BACKOFF_BASE_IN_SECONDS = 2
API_CALL_PARAMS = {
    "audit-trail": {
        "organization_keyword": "organization_id",
        "order_keyword": "order_by",
        "order_value": "recorded_at_asc",
        "timerange_start_keyword": "recorded_after",
        "timerange_end_keyword": "recorded_before",
        "timestamp_keyword": "recorded_at",
        "page_keyword": "page_token",
        "page_size_keyword": "page_size",
        "page_size_value": "100",
    },
    "iam": {
        "organization_keyword": "organization_id",
        "order_keyword": "order_by",
        "order_value": "created_at_asc",
        "timerange_start_keyword": "created_after",
        "timerange_end_keyword": "created_before",
        "timestamp_keyword": "created_at",
        "page_keyword": "page",
        "page_size_keyword": "page_size",
        "page_size_value": "100",
    },
    "instance": {
        "organization_keyword": "organization",
        "order_keyword": "order",
        "order_value": "creation_date_asc",
        "timerange_start_keyword": "_empty_1",
        "timerange_end_keyword": "_empty_2",
        "timestamp_keyword": "creation_date",
        "page_keyword": "page",
        "page_size_keyword": "per_page",
        "page_size_value": "100",
    },
}
API_RESPONSE_LIST_NAME_ALTERNATIVES = ["events", "logs", "users", "groups", "applications", "servers"]
API_RESPONSE_NEXT_PAGE_TOKEN_FIELD = "next_page_token"

LOG_CRITICAL_TAG = "[Scaleway Critical]"
LOG_ERROR_TAG = "[Scaleway Error]"
LOG_WARNING_TAG = "[Scaleway Warning]"
LOG_INFO_TAG = "[Scaleway Info]"
LOG_DEBUG_TAG = "[Scaleway Debug]"
