
# Global variables
INTEGRATION_NAME = "FNC_Splunk_v116"
name = "Splunk Enterprise"

DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

HISTORY_LIMIT = 500
DETECTIONS_ARGUMENTS = [
    'limit',
    'polling_delay',
    'start_date',
    'end_date',
    'account_uuid',
    'pull_muted_rules',
    'pull_muted_devices',
    'pull_muted_detections',
    'status',
    'include_description',
    'include_signature',
    'include_events',
    'include_pdns',
    'include_annotations'
]
