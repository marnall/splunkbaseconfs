"""Shared constants for the Flare Splunk integration."""

# Note: FLARE_API_BASE_URL and token generation are managed by the flareio SDK.
APP_NAME = "flare_splunk_app"
HOST = "localhost"
SPLUNK_PORT = 8089
STORAGE_REALM = "flare_v2_integration_realm"
DEFAULT_BACKFILL_DAYS = 30
DEFAULT_INGESTION_PAGE_SIZE = 10
DEFAULT_INGESTION_INTERVAL_SECONDS = 60
LOG_FILE_NAME = "flare_cron_job.log"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3

# Flare API endpoints
ENDPOINT_TENANTS = "/firework/v2/me/tenants"
ENDPOINT_EVENTS_SEARCH = "/firework/v4/events/tenant/_search"
ENDPOINT_EVENTS_DETAIL = "/firework/v4/events/"
ENDPOINT_FILTER_SEVERITIES = "/firework/v4/events/filters/severities"
ENDPOINT_FILTER_TYPES = "/firework/v4/events/filters/types"

# Splunk storage password keys
KEY_API_KEY = "api_key"
KEY_TENANT_IDS = "tenant_ids"
KEY_INGEST_FULL_EVENT_DATA = "ingest_full_event_data"
KEY_SEVERITIES_FILTER = "severities_filter"
KEY_SOURCE_TYPES_FILTER = "source_types_filter"
KEY_BACKFILL_DAYS = "number_of_days_to_backfill"
KEY_PROXY_ENABLED = "proxy_enabled"
KEY_PROXY_TYPE = "proxy_type"
KEY_PROXY_HOST = "proxy_host"
KEY_PROXY_PORT = "proxy_port"
KEY_PROXY_USERNAME = "proxy_username"
KEY_PROXY_PASSWORD = "proxy_password"
KEY_INDEX_NAME = "index_name"
KEY_SSL_VERIFY = "ssl_verify"
KEY_TENANT_NAMES = "tenant_names"
KEY_LOG_LEVEL = "log_level"
