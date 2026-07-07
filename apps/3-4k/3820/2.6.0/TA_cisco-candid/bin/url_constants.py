#!/usr/bin/python

# API Version
API_V1 = "/nae/api/v1/"

# User Login/Logout
WHO_AM_I = "whoami"
LOGIN = "login"
LOGOUT = "logout"


# Fabric Id
ACI_FABRIC = "config-services/assured-networks/aci-fabric"

# SMART EVENTS
# {0} is placement for fabric id
# {1} is placement for event uuid
SMART_EVENTS_BASE_URL = 'assured-networks/{0}'
SMART_EVENTS_BY_CATEGORY = "event-services/smart-events"
EVENT_CATEGORY_DICT = {
    "TENANT_ROUTING": "/model/aci-routing/tenant-forwarding/smart-events/{1}",
    "POLICY_ANALYSIS": "/model/aci-policy/policy-analysis/smart-events/{1}",
    "END_POINT": "/model/aci-routing/endpoints/smart-events/{1}",
    "SECURITY": "/model/aci-policy/security-adherence/smart-events/{1}",
    "RESOURCE_UTILIZATION": "/model/aci-policy/tcam/smart-events/{1}",
    "SYSTEM": "/smart-events/{1}",
    "COMPLIANCE": "/model/aci-policy/compliance-analysis/smart-events/{1}"
}
EVENTS_BY_CATEGORY_LIST = ['$epoch_id', '$filter', 'category', 'severity', '$page', '$size', '$sort', 'sub_category',
                           'mnemonic']
EVENT_SEVERITY_LIST = ['EVENT_SEVERITY_CRITICAL', 'EVENT_SEVERITY_MAJOR', 'EVENT_SEVERITY_MINOR',
                       'EVENT_SEVERITY_WARNING', 'EVENT_SEVERITY_INFO']

EPOCHS = 'event-services/epochs'
EPOCH_PARAMS = ['$size', '$page', '$epoch_id', '$view', '$start_time', '$end_time','$sort', '$fabric_id', '$from_collection_time_msecs', '$to_collection_time_msecs']
SMART_EVENTS_DETAIL = 'event-services/smart-events/detail'

SMART_EVENT_LIFECYCLE = 'event-services/smart-events/lifecycle'

def api_v1_url(url=None):
    return API_V1 + url
