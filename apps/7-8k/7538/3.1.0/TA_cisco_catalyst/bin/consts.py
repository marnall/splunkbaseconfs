"""Cisco Catalyst TA constants."""

import os
from enum import Enum

import import_declare_test


APP_NAME = "TA_cisco_catalyst"
COLLECTION_NAME = "Splunk_TA_cisco_dnacenter_checkpointer"
CYBERVISION_COLLECTION_NAME = "Splunk_TA_cisco_cyber_vision_checkpointer"
SDWAN_COLLECTION_NAME = "Splunk_TA_cisco_sdwan_checkpointer"
ISE_COLLECTION_NAME = "Splunk_TA_cisco_ise_checkpointer"
ACCOUNT_CONF_FILE = "ta_cisco_catalyst_account"
CYBERVIVSION_ACCOUNT_CONF_FILE = "ta_cisco_catalyst_cyber_vision_account"
CATALYSTC_CERT_FILE_LOC = os.path.join(
    os.environ.get("SPLUNK_HOME"),
    "etc",
    "apps",
    import_declare_test.ta_name,
    "local",
    "custom_certs",
    "dnac_{cert_name}_cert.pem",
)
CYBER_VISION_CERT_FILE_LOC = os.path.join(
    os.environ.get("SPLUNK_HOME"),
    "etc",
    "apps",
    import_declare_test.ta_name,
    "local",
    "custom_certs",
    "cybervision_{cert_name}_cert.pem",
)

# Catalyst Center Constants
AUDIT_LOGS_LIMIT = 25  # Max limit is not defined in the doc. But, 25 is the maximum logs returned in a single call.
CATALYSTC_DEVICE_HEALTH_START_TIME_MINUTES = (
    15  # Data will be collected for last 15 minutes.
)
CLIENT_LIMIT = 20
SITE_TOPOLOGY_LIMIT = 500

# ISE CONSTANTS
ISE_CERT_FILE_LOC = os.path.join(
    os.environ.get("SPLUNK_HOME"),
    "etc",
    "apps",
    import_declare_test.ta_name,
    "local",
    "custom_certs",
    "ise_{cert_name}_cert.pem",
)
ISE_CLIENT_CERT_FILE_LOC = os.path.join(
    os.environ.get("SPLUNK_HOME"),
    "etc",
    "apps",
    import_declare_test.ta_name,
    "local",
    "custom_certs",
    "ise_{cert_name}_pxgrid_client_cert.pem",
)
ISE_AUTH_ENDPOINT = "/api/v1/policy/network-access/policy-set"
REQUEST_RESPONSE_TIMEOUT = 60

ISE_ACCOUNT_CONF_FILE = "ta_cisco_catalyst_ise_account"
ERS_SGT = "/ers/config/sgt"
ERS_API_INPUTS = ["security_group_tags", "ip_sgt_bindings"]
DATA_TYPES = [
    "security_group_tags",
    "authz_policy_hit",
    "ise_tacacs_rule_hit",
    "ip_sgt_bindings",
]

ISE_ENDPOINTS = {
    "SECURITY_GROUPS": "/ers/config/sgt/",
    "SECURITY_GROUPS_DETAILS": "/ers/config/sgt/{id}",
    "DEPLOYMENT_NODE": "/api/v1/deployment/node",
    "AUTH_POLICY": "/api/v1/policy/network-access/policy-set",
    "AUTH_POLICY_DETAILS": "/api/v1/policy/network-access/policy-set/{id}/authorization",
    "DEVICE_POLICY": "/api/v1/policy/device-admin/policy-set",
    "DEVICE_POLICY_DETAILS": "/api/v1/policy/device-admin/policy-set/{id}/authorization",
    "PXGRID_ACCOUNT_CREATE": "/pxgrid/control/AccountCreate",
    "PXGRID_ACCOUNT_ACTIVATE": "/pxgrid/control/AccountActivate",
    "PXGRID_APPROVE_USERNAME": "/ers/config/pxgridNode/name/{pxgrid_client_username}/approve",
    "PXGRID_SERVICELOOKUP": "/pxgrid/control/ServiceLookup",
    "PXGRID_ACCESS_SECRET": "/pxgrid/control/AccessSecret",
    "PXGRID_BINDINGS": "/pxgrid/ise/sxp/getBindings",
    "PXGRID_DELETE_USERNAME": "/ers/config/pxgridnode/name/{pxgrid_client_username}",
}

PXGRID_PORT = "8910"
PXGRID_SERVICE_NAME = "com.cisco.ise.session"
PXGRID_CONTENT_TYPE = "application/json"
PXGRID_ACCEPT = "application/json"

ISE_MAX_WORKERS = 5
ISE_PAGE_SIZE = 100
TIMEOUT = 60 * 2
MAX_RETRIES = 3
BACKOFF_FACTOR = 1
ISE_RETRY_SECONDS = 60  # sleep time in seconds
STATUS_FORCE_LIST = [429]
DEFAULT_ERS_PAGE_SIZE = 100

# SDWAN CONSTANTS
SDWAN_REQUEST_TIMEOUT = 120
SDWAN_CERT_FILE_LOC = os.path.join(
    os.environ.get("SPLUNK_HOME"),
    "etc",
    "apps",
    import_declare_test.ta_name,
    "local",
    "custom_certs",
    "sdwan_{cert_name}_cert.pem",
)
SDWAN_ACCOUNT_CONF_FILE = "ta_cisco_catalyst_sdwan_account"
SDWAN_JSESSIONID_ENDPOINT = "/j_security_check"
SDWAN_TOKEN_ENDPOINT = "/dataservice/client/token"
SDWAN_DEVICE_DETAILS_ENDPOINT = "/dataservice/health/devices"
SDWAN_UTD_HEALTH_ENDPOINT = "/dataservice/device/utd/engine-status"
SDWAN_TUNNEL_HEALTH_ENDPOINT = "/dataservice/statistics/approute/tunnels/health/latency"
SDWAN_SSE_TUNNEL_HEALTH_ENDPOINT = "/dataservice/device/sse/tunnels"
SDWAN_LINK_HEALTH_ENDPOINT = "/dataservice/device/interface"
SDWAN_SITE_HEALTH_ENDPOINT = "/dataservice/statistics/sitehealth/common"
SDWAN_SSE_TUNNELS_ENDPOINT = "/dataservice/device/sig/getSigTunnelList"
SDWAN_MAX_WORKERS = 5
SDWAN_MAX_RETRIES = 3
SDWAN_BACKOFF_FACTOR = 2
SDWAN_DEVICE_PAGE_SIZE = 1000
SDWAN_SSE_TUNNELS_PAGE_SIZE = 5000
SDWAN_CHECKPOINT_WINDOW_IN_MINUTES = 10
SDWAN_TUNNEL_HEALTH_LIMIT = 100000


class Sourcetype(Enum):
    """Enum class for sourcetypes."""

    # SDWAN Sourcetypes
    SDWAN_UTD_HEALTH_SOURCETYPE = "cisco:sdwan:utdhealth"
    SDWAN_TUNNEL_HEALTH_SOURCETYPE = "cisco:sdwan:tunnelhealth"
    SDWAN_LINK_HEALTH_SOURCETYPE = "cisco:sdwan:linkhealth"
    SDWAN_SITE_HEALTH_SOURCETYPE = "cisco:sdwan:sitehealth"
    SDWAN_SSE_TUNNELS_SOURCETYPE = "cisco:sdwan:ssetunnels"

    # ISE SOURCETYPES
    ISE_AUTH_POLICY_SOURCETYPE = "cisco:ise:radius:policyset"
    ISE_AUTH_POLICY_DETAILS_SOURCETYPE = "cisco:ise:radius:authz:policy"
    ISE_DEVICE_POLICY_SOURCETYPE = "cisco:ise:tacacs:policyset"
    ISE_DEVICE_POLICY_DETAILS_SOURCETYPE = "cisco:ise:tacacs:authz:policy"
    ISE_SECURITY_GROUPS_SOURCETYPE = "cisco:ise:securitygroups"
    ISE_SG_MAPPING_SOURCETYPE = "cisco:ise:sgtbindings"
    ISE_REPORTS_DEFAULT_SOURCETYPE = "cisco:ise:analytics"
    ISE_REPORTS_REGISTRY_SOURCETYPE = "cisco:ise:analytics:registry"
    ISE_REPORTS_HARDWARE_SOURCETYPE = "cisco:ise:analytics:hardware"
    ISE_REPORTS_APPLICATIONS_SOURCETYPE = "cisco:ise:analytics:applications"
    ISE_REPORTS_FULLREPORT_SOURCETYPE = "cisco:ise:analytics:fullreport"
