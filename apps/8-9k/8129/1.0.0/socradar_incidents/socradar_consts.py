# -*- coding: utf-8 -*-
"""
SOCRadar SOAR App Constants
"""

# API Configuration
SOCRADAR_API_BASE_URL = "https://platform.socradar.com/api"
API_TIMEOUT_SECONDS = 30
API_MAX_RETRIES = 3
API_RATE_LIMIT_WAIT_INITIAL = 30  # seconds
API_RATE_LIMIT_WAIT_MAX = 60  # seconds

# Pagination
DEFAULT_PAGE_SIZE = 100
DEFAULT_MAX_PAGES = 50
DEFAULT_MAX_INCIDENTS_PER_POLL = 500

# State Management
STATE_MAX_ALARMS = 10000  # Maximum alarms to track in state
STATE_KEY_ALARM_STATUS = "alarm_status"
STATE_KEY_LAST_UPDATED = "last_updated"

# Field Limits
MAX_TEXT_LENGTH = 5000  # Maximum length for text fields before truncation

# App Metadata
APP_VERSION = "1.2.0"
APP_NAME = "SOCRadar Incidents"
USER_AGENT = f"SOAR-SOCRadar/{APP_VERSION}"

# Severity Mapping
SEVERITY_CRITICAL = "critical"
SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"
SEVERITY_LOW = "low"

# Status Values
STATUS_OPEN = "Open"
STATUS_CLOSED = "Closed"
STATUS_IN_PROGRESS = "In Progress"
STATUS_NA = "N/A"

# CEF Types
CEF_TYPE_IP = ["ip"]
CEF_TYPE_URL = ["url"]
CEF_TYPE_DOMAIN = ["domain"]
CEF_TYPE_HASH_SHA256 = ["hash", "sha256"]
CEF_TYPE_HASH_MD5 = ["hash", "md5"]
CEF_TYPE_EMAIL = ["email"]

# Labels
LABEL_SOCRADAR = "socradar"
LABEL_EVENT = "event"
LABEL_NETWORK = "network"

# Error Messages
ERR_MISSING_CONFIG = "Missing company_id or api_key in asset configuration"
ERR_UNAUTHORIZED = "Unauthorized (401). Please check your API key and company ID."
ERR_RATE_LIMIT = "Rate limit exceeded. Please wait and try again."
ERR_CONNECTION = "Connection error: {error}"
ERR_TIMEOUT = "Request timeout after {timeout} seconds"
ERR_INVALID_JSON = "Invalid JSON response from API"
ERR_SAVE_CONTAINER = "Failed to save container: {message}"
ERR_SAVE_ARTIFACT = "Failed to save artifact: {message}"

# Success Messages
MSG_TEST_CONNECTIVITY_PASS = "Successfully connected to SOCRadar API"
MSG_INGESTION_COMPLETE = "Ingestion complete: {new} new/updated, {skipped} skipped"
MSG_NO_MORE_INCIDENTS = "No more incidents to process"

# Progress Messages
MSG_INITIALIZING = "Connector initialized successfully"
MSG_TESTING_CONNECTIVITY = "Testing SOCRadar API connectivity..."
MSG_FETCHING_PAGE = "Fetching page {current}/{total} ({percent}% complete) - {count} incidents processed"
MSG_RATE_LIMIT_WAIT = "Rate limit encountered. Waiting {seconds}s (attempt #{attempt})"
MSG_STATUS_CHANGE = "Status change detected for alarm {alarm_id}: {old} -> {new}"

# SOCRadar Platform URLs
SOCRADAR_PLATFORM_BASE = "https://platform.socradar.com"
SOCRADAR_ALARM_URL_TEMPLATE = "{base}/app/company/{company_id}/alarm-management?tab=approved&alarmId={alarm_id}"