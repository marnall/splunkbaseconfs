from enum import Enum

class Sourcetype(Enum):
    eAssets = "assets"
    eAlerts = "alerts"
    eEvents = "events"
    eBaselines = "baselines"

TOKEN_KEY = "token"
COUNT_TOTAL = "count_total"
COUNT_IN_PAGE = "count_in_page"
OBJECTS_KEY = "objects"
TIMESTAMP_PATTERN = "%Y-%m-%dT%H:%M:%S.%f"
TIMESTAMP_KEY = "timestamp"
EMC_IP_KEY = "emc_ip"
EMC_ADMIN_ACCOUNT_KEY = "emc_admin_account"
ACTIONABLE_ASSETS_KEY = "actionable_assets"
ASSET_ROLE_KEY = "role"
ASSET_ROLE_PRIMARY = 5
ASSET_KEY = "asset"
IPV4_KEY = "ipv4"
IPV6_KEY = "ipv6"
DEFAULT_TIMESTAMP = "0"
SITE_ID_KEY = "site_id"
ALERT_ID_KEY = "alert_id"
PER_PAGE = 200
INPUT_FROM_TIMESTAMP_KEY = "from_timestamp"
INPUT_NOTIFICATIONS_EMAIL_KEY = "notification_email"
NOTIFICATIONS_ERROR_MSG = "Something went wrong while fetching {} from Claroty EMC's API. Please check the add-on's logs"
NOTIFICATIONS_RESOLVED_MSG = "The fetching Claroty's {} from EMC's API issue was resolved."
SSL_PORT = 465
TLS_PORT = 587
EMAIL_ADDRESSES_SEPARATOR = ","
NOTIFICATIONS_EMAIL_SUBJECT = "Claroty add-on for Splunk Notifications - {}"
EMAIL_FROM_ADDRESS = "Claroty add-on for Splunk"
LAST_UPDATED_KEY = "last_updated"
ONE_MICROSECOND_AS_SEC = 1 / 1000000
QUERY_FILTER_MULTIPLE_VALUES_SEPARATOR = ',;$'
QUERY_FILTERS_CONCATENATOR = '&'
SITES_FILTER_KEY = "sites"
MULTIPLE_INPUT_SEPARATOR = ","
RANGE_INPUT_SIGN = "-"
URL_QUERY_PAGE_TEMPLATE = '{page}'
LOOKUP_EXACT = "exact"
LOOKUP_GREATER_THAN = "gt"
LOOKUP_GREATER_THAN_EQUAL = "gte"
LOOKUP_LESS_THAN = "lt"
LOOKUP_LESS_THAN_EQUAL = "lte"
TYPE_QUERY_FILTER_KEY = "type"
SITE_ID_QUERY_FILTER_ATTRIBUTE = "site_id"
SPLUNK_MULTIPLE_INPUT_FIELD_DEF_VALUE = '[]'
ASSET_TYPE_LABLE_KEY = "asset_type__"
MITRE_ID_KEY = "mitre_id"
MITRE_TECHNIQUES_KEY = "mitre_techniques"
ASSIGNED_TO_KEY = "assigned_to"
TIMEZONE_PATTERN = r"[+-]\d{2}:\d{2}$"
RESOURCE_ID_KEY = "resource_id"
HTTP_REQUEST_TIMEOUT = 180

API_ENDPOINTS = {
    Sourcetype.eAssets: "/ranger/assets",
    Sourcetype.eAlerts: "/ranger/alerts",
    Sourcetype.eEvents: "/ranger/events",
    Sourcetype.eBaselines: "/ranger/baselines"
}

