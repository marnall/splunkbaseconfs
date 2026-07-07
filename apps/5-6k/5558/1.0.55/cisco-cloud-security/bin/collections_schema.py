"""
Splunk KVStore Collections Schema Definitions

This module defines the schema for all KVStore collections used in the
Cisco Cloud Security app.`  
"""

from enum import Enum
from typing import Union
from logger import Logger


class BaseCollectionFields(str, Enum):
    """
    Base class for all KVStore collection field enums.
    Provides field validation functionality.
    """

class CloudlockFields(BaseCollectionFields):
    """Field names for cloudlock collection."""
    NAME = "name"
    TOKEN = "token"
    URL = "url"


class CloudlockV2TosFields(BaseCollectionFields):
    """Field names for cloudlock-v2-tos collection."""
    CUST_NAME = "CustName"
    CUST_DATE = "CustDate"
    CUST_VERSION = "CustVersion"


class CloudlockV2Fields(BaseCollectionFields):
    """Field names for cloudlock-v2 collection."""
    INVESTIGATE_NAME = "investigateName"
    INVESTIGATE_URL = "investigateURL"
    INVESTIGATE_TOKEN = "investigateToken"
    CLOUDLOCK_NAME = "cloudlockName"
    CLOUDLOCK_URL = "cloudlockURL"
    CLOUDLOCK_TOKEN = "cloudlockToken"
    CLOUDLOCK_INCIDENT_DETAILS = "cloudlockIncidentDetails"
    CLOUDLOCK_INCIDENT_UEBA = "cloudlockIncidentUEBA"
    ENFORCEMENT_NAME = "enforcementName"
    ENFORCEMENT_URL = "enforcementURL"
    ENFORCEMENT_TOKEN = "enforcementToken"
    CREATED_DATE = "createdDate"
    POLLING_INTERVAL = "pollingInterval"
    USER_NAME = "userName"


class InvestigateHealthCheckFields(BaseCollectionFields):
    """Field names for investigate_health_check collection."""
    INVESTIGATE_URL = "investigateURL"
    INVESTIGATE_URL_STATUS = "investigateURLStatus"
    INVESTIGATE_LAST_INVOCATION_DATE = "investigateLastInvocationDate"
    INVESTIGATE_RESPONSE_TIME = "investigateResponseTime"


class CloudlockHealthCheckFields(BaseCollectionFields):
    """Field names for cloudlock_health_check collection."""
    CLOUDLOCK_URL = "cloudlockURL"
    CLOUDLOCK_URL_STATUS = "cloudlockURLStatus"
    CLOUDLOCK_LAST_INVOCATION_DATE = "cloudlockLastInvocationDate"
    CLOUDLOCK_RESPONSE_TIME = "cloudlockResponseTime"


class DestinationListsHealthCheckFields(BaseCollectionFields):
    """Field names for destination_lists_health_check collection."""
    DESTINATION_LISTS_URL = "destinationListsURL"
    DESTINATION_LISTS_URL_STATUS = "destinationListsURLStatus"
    DESTINATION_LISTS_LAST_INVOCATION_DATE = "destinationListsLastInvocationDate"
    DESTINATION_LISTS_RESPONSE_TIME = "destinationListsResponseTime"


class InvestigateSettingsFields(BaseCollectionFields):
    """Field names for investigate_settings collection."""
    USER_NAME = "userName"
    CREATED_DATE = "createdDate"
    CONFIG_NAME = "configName"
    INDEX = "index"
    STATUS = "status"
    ORG_ID = "orgId"


class OAuthSettingsFields(BaseCollectionFields):
    """Field names for oauth_settings collection."""
    BASE_URL = "baseURL"
    USER_NAME = "userName"
    API_KEY = "apiKey"
    API_SECRET = "apiSecret"
    TIMEZONE = "timezone"
    STORAGE_REGION = "storageRegion"
    CREATED_DATE = "createdDate"
    CONFIG_NAME = "configName"
    STATUS = "status"
    MODIFICATION_STATUS = "modificationStatus"
    ORG_ID = "orgId"


class GlobalOrgFields(BaseCollectionFields):
    """Field names for global_org collection."""
    ORG_ID = "orgId"


class CloudlockSettingsFields(BaseCollectionFields):
    """Field names for cloudlock_settings collection."""
    USER_NAME = "userName"
    CREATED_DATE = "createdDate"
    CONFIG_NAME = "configName"
    URL = "url"
    TOKEN = "token"
    SHOW_INCIDENT_DETAILS = "showIncidentDetails"
    SHOW_UEBA = "showUEBA"
    STATUS = "status"
    CLOUDLOCK_START_DATE = "cloudlock_start_date"


class SelectedDestinationListsFields(BaseCollectionFields):
    """Field names for selected_destination_lists collection."""
    DEST_LIST_ID = "dest_list_id"
    DEST_LIST_NAME = "dest_list_name"
    ROLE = "role"


class CloudlockV2KeystoreFields(BaseCollectionFields):
    """Field names for cloudlock_v2_keystore collection."""
    KEYVAL = "keyval"


class DomainStatusFields(BaseCollectionFields):
    """Field names for domain_status collection."""
    DOM_STAT = "dom_stat"


class DestinationsFields(BaseCollectionFields):
    """Field names for destinations collection."""
    NAME = "name"
    ID = "id"
    COMMENT = "comment"
    STATUS = "status"
    ACTION = "action"
    SOURCE = "source"
    LOGGED_IN_USER = "loggedinuser"
    MODIFICATION_TIME = "modificationtime"
    DESTINATION_LIST_ID = "destinationListId"
    DESTINATION_LIST_NAME = "destinationListName"


class RefreshRateFields(BaseCollectionFields):
    """Field names for refresh_rate collection."""
    REFRESH_RATE = "refresh_rate"


class S3IndexesFields(BaseCollectionFields):
    """Field names for s3_indexes collection."""
    DNS_INDEX = "dns_index"
    PROXY_INDEX = "proxy_index"
    FIREWALL_INDEX = "firewall_index"
    DLP_INDEX = "dlp_index"
    RAVPN_INDEX = "ravpn_index"
    CREATED_DATE = "createdDate"


class CloudlockIndexFields(BaseCollectionFields):
    """Field names for cloudlock_index collection."""
    INDEX = "index"


class AppDiscoveryIndexFields(BaseCollectionFields):
    """Field names for appdiscovery_index collection."""
    INDEX = "index"
    ORG_ID = "orgId"


class AlertsIndexFields(BaseCollectionFields):
    """Field names for alerts_index collection."""
    INDEX = "index"
    ORG_ID = "orgId"


class PrivateAppIndexFields(BaseCollectionFields):
    """Field names for privateapp_index collection."""
    INDEX = "index"
    ORG_ID = "orgId"


class DashboardSettingsFields(BaseCollectionFields):
    """Field names for dashboard_settings collection."""
    SEARCH_INTERVAL = "search_interval"