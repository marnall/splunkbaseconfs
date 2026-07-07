# Netskope Web Transactions V2
NO_PROXY = "localhost,127.0.0.1,0.0.0.0,localaddress"

# Waterfall Model
FAILED_WINDOW_RETRIES = 3
RECURSIVE_DEPTH_LEVEL = 1

# Iterator
ALERTS_TIMEOUT = 30
EVENTS_TIMEOUT = 30
CLIENTS_TIMEOUT = 30
ITERATOR_TIMEOUT = 30
ITERATOR_INTERVAL_SEC = 0
ITERATOR_WAIT_TIME = 30
ITERATOR_DEFAULT_STARTDATETIME_DAYS_BACK = 0
RETRY_BACKOFF_MULTIPLIER = 2**6
RETRY_COUNT = 6
IS_FIRST_CALL = True
# Real-Time
REALTIME_QUERY_INTERVAL_SEC = 30
REALTIME_WINDOW_DIVISOR = 3
REALTIME_THREAD_COUNT = 2
REALTIME_INTERVAL_SEC = 30
REALTIME_MAX_OLD_CHECKPOINT = 3600

# Historical
HISTORICAL_QUERY_INTERVAL_SEC = 720
HISTORICAL_WINDOW_DIVISOR = 3
HISTORICAL_THREAD_COUNT = 1
HISTORICAL_INTERVAL_SEC = 0
HISTORICAL_DEFAULT_STARTDATETIME_DAYS_BACK = 7

# Netskope API
NETSKOPE_TIMEOUT = 2 * 60
NETSKOPE_RETRIES = 1
NETSKOPE_BACKOFF_FACTOR = 2
NETSKOPE_VERIFY_SSL = True
NETSKOPE_MAX_DAYS_BACK = 90

# Mapping
EVENT_TYPE_MAPPING = {
    "connection": "page",
    "audit": "audit",
    "application": "application",
    "infrastructure": "infrastructure",
    "client": "client",
    "network": "network",
    "incident": "incident",
    "endpoint": "endpoint"
}

# Events Type Mapping for CSV Input
EVENT_TYPE_MAPPING_CSV = {
    "connection": "page",
    "application": "application",
    "network": "network",
}

ALERT_TYPES = ["All", "compromisedcredential", "ctep", "dlp", "malsite", "malware",
               "policy", "quarantine", "remediation", "securityassessment", "uba", "watchlist", "device", "content"]

REVERSE_ALERT_TYPE_MAPPING = {
    "compromisedcredential": "alert",
    "ctep": "alert",
    "dlp": "alert",
    "malsite": "alert",
    "malware": "alert",
    "policy": "alert",
    "quarantine": "alert",
    "remediation": "alert",
    "securityassessment": "alert",
    "uba": "alert",
    "watchlist": "alert",
    "device": "alert",
    "content": "alert",
    "alert": "alert"
}

ALERT_TYPE_MAPPING = {
    "compromised_credential": "Compromised Credential",
    "security_assessment": "Security Assessment",
    "remediation": "Remediation",
    "legal_hold": "Legal Hold",
    "malware": "Malware",
    "dlp": "DLP",
    "malsite": "malsite",
    "anomaly": "anomaly",
    "policy": "policy",
    "watchlist": "watchlist",
    "quarantine": "quarantine",
    "uba": "uba",
    "device": "device",
    "content": "content",
}

# Conf Manager methods constants.
MODINPUT_NAME = "netskope_events_v2"
SETTINGS_CONF_FILE_NAME = "ta_netskopeappforsplunk_settings"
ACCOUNTS_CONF_FILE_NAME = "ta_netskopeappforsplunk_account"
INPUTS_CONF_FILE_NAME = "inputs"
APP_NAME = "TA-NetSkopeAppForSplunk"
SCRIPTED_INPUT_PARAMETERS_STANZA_NAME = "scripted_input_parameters"
INPUT_INTERVAL = 0

# Checkpoint methods constants.
CHECKPOINT_COLLECTION_NAME = "TA_NetSkopeAppForSplunk_scripted_input_checkpointer"
INPUT_NAME = "netskope_events_v2://netskope_events_v2_{INPUT_NAME}"
NEXT_START_TIME = "start_time_{START_TIME}"
UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
IS_SAFE_TO_DELETE_FLAG = "is_safe_to_delete"
SPLUNKD_URI = "https://127.0.0.1:8089"

# Input parameters constants.
ACCOUNT_NAME = "account_name"
TYPE = "type"
START_DATETIME = "start_datetime"
DATA_COLLECTION_WINDOW = "data_collection_window"
INDEX = "index"
MAX_ACTIVE_INPUTS = "max_active_inputs"
END_DATETIME = "end_datetime"
USER_END_DATETIME = "user_end_datetime"

# User Lookup CSV File
FILE_NAME = "user_data.csv"
USER_EMAIL = "USER_EMAIL"
USER_GROUP = "USER_GROUP"


# Multi Iterator Inputs
ITERATOR_COMMON_URL = "https://{hostname}/api/v2/events/dataexport/iterator/{iterator_name}"
ITERATOR_GET_DATA_URL = "https://{hostname}/api/v2/events/dataexport/iterator/{iterator_name}/events"
MAX_RETRIES = 3
BACKOFF_FACTOR = 1
STATUS_FORCE_LIST = [429]
CHUNK_SIZE = 1000
