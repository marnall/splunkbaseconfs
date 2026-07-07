from enum import Enum, auto

# HTTP error messages
METHOD_NOT_ALLOWED = "Method not allowed"
MISSING_SUMMARIZATION_ID = "Missing summarization_id"
PATH_INFO = "path_info"
REST_PATH = "rest_path"

# ITSI Base Endpoint URI
ITSI_APP_NAME = "SA-ITOA"
ITSI_APP_OWNER = "nobody"
ITSI_BASE_URI = "itoa_interface"
ITSI_SUMMARY_ORCHESTRATOR_URI = ITSI_BASE_URI + "/summarization_action"
ITSI_GET_SEVERITY_URI = "configs/conf-itsi_notable_event_severity"

# ITSI Summarize API Endpoint URI
ITSI_SUMMARIZE_API_BASE_PATH = "/api/v1/itsi_summaries/summarize"
ITSI_HEALTH_API_BASE_PATH = "/api/v1/itsi_summaries/health"

# Summarization status codes
STATUS_INITIATED = 1
STATUS_IN_PROGRESS = 2
STATUS_SUCCESS = 3
STATUS_FAILED = 4
STATUS_TERMINATED = 5

# Constants for interacting with ITSI Summary Orchestrator
STATUS = "status"
ERROR_MESSAGE = "error_message"
SUMMARIZATION = "summarization"
SUMMARIZATION_ID = "summarization_id"
UPDATE_SUMMARIZATION = "update_summarization"
NAME = "name"
ARGUMENTS = "arguments"
ARGS = "args"
RETURN_TYPE = "return_type"
DICT = "dict"
STR = "str"
SERVICE_IDS = "service_ids"
LIST = "list"
GET_ALL_ALERTS = "get_all_alerts"
TARGET_TYPE = "target_type"
EPISODE = "episode"
# Constants for ITSI Summary Orchestrator - construct payload
ALERT_STRING = "alert_string"
ALERT_INFO = "alert_info"
CORRELATIONS = "correlations"
LOGS = "logs"
STEPS_CHECKED = "steps_checked"
SERVICES_TOPOLOGY = "services_topology"
ITSI_REQ_ID = "x-request-id"

# Constants for Summarization Actions
GET_IMPACTED_SERVICE_ID_AND_KPI_ID = "get_impacted_services_and_kpis"
GET_IMPACTED_ENTITIES = "get_impacted_entities"
GET_TIMELINE_SPLS = "get_timeline_spls"
GET_SERVICES_TOPOLOGY = "get_services_topology"
GET_AND_CLEAN_ALERTS = "get_and_clean_alerts"
GET_KPI_AND_ENTITY_TS = "get_kpi_and_entity_ts"
GET_SERVICE_IMPACT_ANALYSIS = "get_service_impact_analysis"

# constants for Summarization Actions - field names
SERVICE_ID = "service_id"
SERVICE_NAME = "service_name"
# SERVICE_IDS is a list of service id, it is used to get service topology and impacted kpis and entities
SERVICE_IDS = "service_ids"
KPI_ID = "kpiid"
KPI_NAME = "kpi_name"
ENTITY_ID = "entity_id"
ENTITY_NAME = "entity_name"
IMPACTED_SERVICES = "impacted_services"
IMPACTED_KPIS = "impacted_kpis"
KPI_SPL = "kpi_spl"
ENTITY_SPL = "entity_spl"
SERVICE_SPL = "service_spl"
GET_CUSTOM_QUERIES = "get_custom_queries"
GET_EPISODE = "get_episode"

# Constants for Splunk KV Store
ITSI_SUMMARY_WORK_QUEUE = "itsi_summary_work_queue"
ITSI_SUMMARY_WORKER_LOGGER_NAME = "itsi_ai_summary_worker"
KVSTORE_KEY = "_key"
CREATED_AT = "created_at"
UPDATED_AT = "updated_at"
ATTEMPTS = "attempts"

PRIORITY = "priority"
FORM = "form"
# Priority levels
PRIORITY_LOW = 0
PRIORITY_HIGH = 1
INVALID_PRIORITY = "invalid_priority"

# Summarization task executor status constants
SUMMARY_TASK_STATUS_SUCCESS = "success"
SUMMARY_TASK_STATUS_FAILED = "failed"
SUMMARY_RESPONSE = "summary_response"

# Constants for time series analysis
VALUE_COLUMN = "alert_value"
TIME_COLUMN = "_time"
KPI_GROUP_COLUMN = "itsi_kpi_id"
ENTITY_GROUP_COLUMN = "entity_title"

# resample unit for the denoising
# 5T means 5 minutes
RESAMPLE_INTERVAL = "5T"

class MissingValueStrategy(Enum):
    NONE = "none"
    FFILL_BFILL = "ffill_bfill"

class ConstantStatus(Enum):
    BOTH_CONSTANT = auto()
    ONE_CONSTANT = auto()
    NONE_CONSTANT = auto()
SUMMARY_RESPONSE = "summary_response"

# Constants for SPL Job Manager
SPL_QUERY_WAITING_INTERVAL = 2  # Interval in seconds for checking job status
SPL_QUERY_TIME_OUT = 300  # Timeout in seconds for job completion

SCS_TOKEN_ENDPOINT: str = "/services/authorization/scs_tokens"
SUMMARY_RESPONSE = "summary_response"

# Constants for alerts
DRILLDOWN_PREFIXES = [
    "itsiDrilldown",
    "drilldown_"
]
COLUMNS_TO_DROP = [
    "_raw",
    "_bkt",
    "_indextime",
    "_serial",
    "_si",
    "_subsecond",
    "event_field_max_length",
    "event_identifier_hash",
    "index",
    "is_use_event_time",
    "itsiDrilldownURI",
    "itsiDrilldownWeb",
    "itsi_action_rule_keys",
    "itsi_earliest_event_time",
    "itsi_first_event_id",
    "itsi_first_event_time",
    "itsi_group_assignee",
    "itsi_group_count",
    "itsi_group_id",
    "itsi_instruction",
    "itsi_is_first_event",
    "itsi_is_last_event",
    "itsi_last_event_time",
    "itsi_parent_group_id",
    "itsi_policy_id",
    "itsi_split_by_hash",
    "linecount",
    "orig_index",
    "orig_raw",
    "orig_rid",
    "orig_sid",
    "owner",
    "punct",
    "rid",
    "splunk_server",
    "event_identifier_fields",
    "mod_time",
    "orig_time",
    "orig_sourcetype",
    "sourcetype",
    "itsi_group_status",
    "status",
    "itsi_aice_fields_matched",
    "itsi_aice_fields_not_matched",
    "itsi_is_aice_enabled",
]
ADDITIONAL_COLUMNS_TO_DROP = ["_time", "eventId", "event_id", "itsi_service_ids", "parentserviceid", "itsi_service_topology_hierarchy_level"]
EVENT_ID_COLUMN = "event_id"
SPL_KEY = "spl"
EVENT_IDENTIFIER_STRING = "event_identifier_string"

# Constants for timeseries data collection
ENTITY_FROM_KPI_ID = "entity_from_kpi_id"
KPI_TS_KEY = "kpi"
ENTITY_TS_KEY = "entity"
GRAPHS = "graphs"
EDGES = "edges"
TARGET_VERTEX = "target"
SOURCE_VERTEX = "source"
VERTICES = "vertices"
ID = "id" # this id is the node id in the topology graph
NODE_DEPTH = "nodeDepth"
TIME_ZONE_UTC = "UTC"
# Default correlation threshold for selecting correlated time series  
DEFAULT_CORRELATION_THRESHOLD = 0.7
# Maximum lag steps to consider for correlation
DEFAULT_MAX_LAG = 6
# this is the lookback offset for adjusting the window for time series correlation 
# effective_start_time = episode_start_time - lookback_offset
DEFAULT_LOOKBACK_OFFSET = "1h"
# Constants used to convert lagging into readable string
# unit translation
SECONDS_IN_DAY = 86400
SECONDS_IN_HOUR = 3600
SECONDS_IN_MINUTE = 60
class CorrelationModelSelection(Enum):
    PEARSON = "pearson"
    # Future models can be added here, e.g. GRANGER = "granger", DTW = "dtw"

# constants for service impact analysis
SERVICE_IMPACT_ANALYSIS = "service_impact_analysis" # field name 
SIA_RANKING_FIELD = "severity" # SIA is short for Service Impact Analysis, we use severity as the ranking field
KPI_KEY = "_key" # in response of service impact analysis tool, _key field means kpiid
class KPISEVERITY(Enum):
    """Enum for KPI severity levels."""
    CRITICAL = 6
    HIGH = 5
    MEDIUM = 4
    LOW = 3
    NORMAL = 2
    INFO = 1
DEFAULT_SEVERITY_FOR_MISSING_FIELD = KPISEVERITY.INFO.value

DESCRIPTION_KEY = "description"
DATA_STRING_KEY = "data_string"
TITLE_KEY = "title"
FIELDS_KEY = "fields"
TYPE_KEY = "type"

ONE_HOUR_IN_SEC = 3600
ONE_SEC = 1

LOG_COLUMNS_TO_DROP = ["source", "sourcetype", "index", "host", "linecount", "splunk_server"]

STATUS_OK = 200
STATUS_ERROR = 500
CHECKED_IMPACTED_ITEMS = "checked_impacted_items"
CHECKED_ALERTS = "checked_alerts"
CHECKED_SUMMARY_DATA = "checked_summary_data"
CHECKED_TOPOLOGY_DATA = "checked_topology_data"
CHECKED_SERVICE_IMPACT_ANALYSIS = "checked_service_impact_analysis"
CUSTOM_QUERIES_DATA = "custom_queries_data"

TYPES_KEY = "types"
RAW_COLUMN_KEY = "_raw"
CLUSTER_COUNT_KEY = "cluster_count"

START_UNIX_TIMESTAMP = "<timestamp format=\"Unix\">"
END_UNIX_TIMESTAMP = "</timestamp>"

# Required columns to always retain for LLM prompt in alerts processing
REQUIRED_COLUMNS = [
    'severity',
    'entity_key',
    '_time',
    'search_name',
    'itsi_group_id',
    'itsi_policy_id',
    'itsi_service_ids',
    'event_identifier_string',
    'source',
    'Title',
    'title',
    'description',
    'src',
    'event_id'
]
class ErrorMessage(Enum):
    ERROR_PAYLOAD_CONSTRUCTION_FAILED = "Unable to complete due to an error fetching data for summarization."
    ERROR_LLM_CALL_FROM_SCS_FAILED = "Unable to complete due to an error generating summary."

SEVERITY_ID = "severity"
SEVERITY_LABEL_INFO = "Info"
DEFAULT_SEVERITY_ID_CRITICAL = "6"
SEVERITY_LABEL_CRITICAL = "Critical"
LARGE_EPISODE_THRESHOLD = 10

UNKNOWN = "unknown"