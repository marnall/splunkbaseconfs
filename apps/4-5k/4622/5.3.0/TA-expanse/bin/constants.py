from enum import Enum

COMPLETED_STATUS = 'completed'
LAST_RUN_RISKY_FLOWS = 'last_run_risky_flows'
LAST_REFRESH_IP_RANGES = 'last_refresh_ipranges'
LAST_REFRESH_IPS = 'last_refresh_ips'
LAST_RUN_ALERTS = 'last_run_alerts'
RETRY_ALERT_IDS = 'retry_alert_ids'
DEDUP_ALERT_IDS = 'dedup_alert_ids'
LAST_REFRESH_CERTIFICATES = 'last_refresh_certificates'
LAST_REFRESH_DOMAINS = 'last_refresh_domains'
LAST_REFRESH_SERVICES = 'last_refresh_services'
LAST_REFRESH_RESPONSIVE_IPS = 'last_refresh_responsive_ips'
LAST_REFRESH_CLOUD_RESOURCES = 'last_refresh_cloud_resources'
ALERTS_TIME_FORMAT = '%Y-%m-%dT%H:%M:00'
SPLUNK_EVENT_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
SPLUNK_CERT_TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
SPLUNK_CLIENT_PAGE_LIMIT = 50000

# Data Types
IP_RANGE = 'ip_range'
RESPONSIVE_IP = 'responsive_ip'
CERTIFICATES = 'certificates'
DOMAINS = 'domains'
SERVICES = 'services'
CLOUD_ASSETS = 'cloud_assets'

# JSON Data Paths
EXPANSE_OBJECT_DATA_PATH = 'data'
FLOW_DATE_PATH = 'created'
ALERT_UPDATE_DATE_PATH = 'event_timestamp'
UPDATED_FLOW_DATE_PATH = 'flow_created'
UPDATED_ISSUE_UPDATE_DATE_PATH = 'creation_time'
ALERT_ID_PATH = 'alert_id'
IP_ADDRESS_PATH = 'ip'
PAGINATION_ROOT_PATH = 'pagination'
PAGINATION_NEXT_PATH = 'next'
CERTIFICATE_PATH = 'certificate'
MD5_HASH_PATH = 'md5Hash'
DOMAIN_PATH = 'domain'
SERVICE_PATH = 'name'
CIDR_PATH = 'cidr'
REGISTRATION_INFO_PATH = 'relatedRegistrationInformation'

FLOW_DIRECTION = 'flowDirection'
INTERNAL_ADDRESS = 'internalAddress'
EXTERNAL_ADDRESS = 'externalAddress'
INTERNAL_PORT = 'internalPort'
EXTERNAL_PORT = 'externalPort'
PROTOCOL = 'protocol'
OBSERVATION_TIMESTAMP = 'observationTimestamp'

CIM_TIME_ADDRESS = 'server_creation_time'
CIM_DIRECTION_ADDRESS = 'direction'
CIM_SRC_IP_ADDRESS = 'src_ip'
CIM_SRC_PORT_ADDRESS = 'src_port'
CIM_DEST_IP_ADDRESS = 'dest_ip'
CIM_DEST_PORT_ADDRESS = 'dest_port'
CIM_TRANSPORT_ADDRESS = 'transport'

IP_RANGE_DATA_COLLECTION_NAME = "xpanseipranges"
CERTIFICATE_COLLECTION_NAME = "xpansecertificates"
DOMAINS_COLLECTION_NAME = "xpansedomains"
SERVICES_COLLECTION_NAME = "xpanseservices"
UNASSOCIATED_IP_RANGE_NAME = "xpanseresponsiveips"
CLOUD_ASSETS_COLLECTION_NAME = "xpansecloudassets"


class CIM(Enum):
    ENDPOINT = 'endpoint'


class FlowDirections(Enum):
    INBOUND = 'inbound'
    OUTBOUND = 'outbound'
    AMBIGUOUS = 'ambiguous'
    UNKNOWN = 'unknown'


class EndpointCheckpoints(Enum):
    RISKY_FLOWS = 'risky_flows'
    ALERTS_UPDATES = 'alerts_updates'
