"""A module to represent the constants """

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from collections_schema import BaseCollectionFields
from logger import Logger


class Constants(Enum):
    OAUTH_TOKEN_ENDPOINT = '/auth/v2/token'
    TOKEN_EXPIRY = 60


# Shared alert label mappings used by alert_dashboard_index.py and alerts_dashboard_api_client.py
ALERT_SEVERITY_LABEL_MAP = {1: 'High', 2: 'Medium', 3: 'Low', 4: 'Info'}
ALERT_STATUS_LABEL_MAP = {1: 'Active', 2: 'Dismissed', 3: 'Resolved', 4: 'Archived'}


class KvStoreFilterQueries:
    """
    Manages predefined and templated KVStore filter queries.
    """
    FILTER_ORGID_RECORDS_QUERY = {"orgId": {"$gt": ""}}
    ACTIVE_OAUTH_ORG_RECORD_QUERY = {"orgId": {"$gt": ""}, "status": "active"}

    @staticmethod
    def equals(field: BaseCollectionFields, value: str) -> dict:
        """Generates an equality filter query."""
        field_str = field.value if isinstance(field, BaseCollectionFields) else str(field)
        return {field_str: value}

class KvStoreCollections(Enum):
    """Enum representation for kv store collections"""
    INVESTIGATE_SETTINGS = 'investigate_settings'
    CLOUDLOCK_SETTINGS = 'cloudlock_settings'
    OAUTH_SETTINGS = 'oauth_settings'
    S3_INDEXES = 's3_indexes'
    ORG_ACCOUNTS = 'org_accounts'
    PRIVATEAPP_INDEXES = 'privateapp_index'
    APPDISCOVERY_INDEXES = 'appdiscovery_index'
    ALERTS_INDEXES = 'alerts_index'
    SELECTED_DESTINATION_LISTS = 'selected_destination_lists'
    DESTINATIONS = 'destinations'
    GLOBAL_ORG = 'global_org'
    CISCO_INVESTIGATE_DOMAINS = 'cisco_investigate_domains'
    CISCO_INVESTIGATE_IPS = 'cisco_investigate_ips'
    CISCO_INVESTIGATE_HASHES = 'cisco_investigate_hashes'
    CISCO_INVESTIGATE_URLS = 'cisco_investigate_urls'
    ALERT_INPUTS = 'alert_inputs'

@dataclass
class KvStoreRecordsPagination:
    """Dataclass representation for kv store pagination"""
    limit: int
    skip: int
    sort_by: Optional[str] = None
    sort_direction: Optional[int] = None

@dataclass
class KvStorePaginatedRecords:
    """Dataclass representation for kv store paginated records"""
    total_records: int
    records: list

class OAuthSettingsStatus(Enum):
    """Enum representation for oauth settings status"""
    ACTIVE = 'active'
    INACTIVE = 'inactive'

class OAuthSettingsModificationStatus(Enum):
    CREATED = 'created'
    UPDATED = 'updated'
    DELETED = 'deleted'


class UmbrellaReportingAPIEndpoints(Enum):
    """Enum representation for umbrella reporting api endpoints"""

    TOTAL_REQUESTS = '/total-requests/{0}?from={1}&to={2}&limit=1&offset=0&timezone={3}'
    TOTAL_BLOCKED_REQUESTS = '/total-requests/{0}?from={1}&to={2}&limit=1&offset=0&timezone={3}&verdict=blocked'
    REQUESTS_BY_TIME_RANGE = '/requests-by-timerange/{0}?from={1}&to={2}&limit=5000&offset=0&timezone={3}'
    TOP_CATEGORIES = '/top-categories/{0}?from={1}&to={2}&limit=10&offset=0&verdict=blocked&timezone={3}'


class PrivateResourcesEndpoints(Enum):
    """Enum representation for private resources api endpoints"""

    DETAILED_STATS_TIMERANGE = '/private-resources/detailed-stats-timerange?from={0}&to={1}&privateresourceid={2}&timezone={3}'
    DETAILED_STATS_IDENTITIES = '/private-resources/detailed-stats-identities?from={0}&to={1}&privateresourceid={2}&limit={3}&offset={4}&timezone={5}'
    REQUESTS_BY_TIME_RANGE = '/requests-by-timerange?from={0}&to={1}&limit=5000&offset=0&timezone={2}&exists=privateapplicationid&sse=true'
    SUMMARY_STATS = '/private-resources/summary-stats?from={0}&to={1}&limit={2}&offset={3}&timezone={4}'
    TOP_RESOURCES = '/top-resources?from={0}&to={1}&limit={2}&offset={3}&timezone={4}'
    UNIQUE_IDENTITIES = '/unique-identities?from={0}&to={1}&timezone={2}&exists=privateapplicationid&identitytypes=directory_user'
    UNIQUE_RESOURCES = '/unique-resources?from={0}&to={1}&timezone={2}&exists=privateapplicationid'
    PRIVATE_RESOURCE = '/policies/v2/privateResources/{0}'
    PRIVATE_RESOURCE_GROUP = '/policies/v2/privateResourceGroups/{0}'

class APIUsageDashboardAPIEndpoints(Enum):
    """Enum representation for API usage dashboard api endpoints"""
    GET_REQUESTS = "/apiUsage/requests?from={0}&to={1}&userAgents={2}"
    GET_RESPONSES = "/apiUsage/responses?from={0}&to={1}&userAgents={2}"
    GET_KEYS = "/apiUsage/keys?from={0}&to={1}&userAgents={2}"
    GET_SUMMARY = "/apiUsage/summary?from={0}&to={1}&userAgents={2}"
    OPTIONAL_PARAMS = ["apiKeys", "paths", "verbs", "statusCodes"]

class CloudSecurityAPIEndpoints(Enum):
    """Enum representation for umbrella cloud security api endpoints"""

    TOTAL_REQUESTS_TREND = '/requests-by-timerange?from={0}&to={1}&limit=5000&offset=0&timezone={2}'
    SECURITY_REQUESTS_TREND = '/requests-by-timerange?from={0}&to={1}&limit=5000&offset=0' \
                              '&timezone={2}&verdict=blocked&categories=65,64,150,110,61,66,67,86,108,68,109,87'


class AlertingAPIEndpoints(Enum):
    """Enum representation for alerting api endpoints"""

    LIST_ALERTS = '/admin/v2/alerting/alerts?orgId={0}&limit={1}&offset={2}'
    GET_ALERT_COUNT = '/admin/v2/alerting/alerts?orgId={0}&limit=1&offset=0'
    UPDATE_ALERTS_STATUS = '/admin/v2/alerting/alerts/status?orgId={0}'
    GET_ALERT_DETAILS = '/admin/v2/alerting/alerts/{1}?orgId={0}'


class AppDiscoveryAPIEndpoints(Enum):
    """Enum representation for umbrella app discovery api endpoints"""

    TOTAL_COUNT = '/reports/v2/appDiscovery/appDiscoveryStats'
    LIST_APPLICATIONS = '/appDiscovery/applications?limit={0}&offset={1}&timezone={2}&sort={3}&order={4}'
    GET_APP_DETAILS = '/appDiscovery/applications/{0}?timezone={1}'
    GET_APP_IDENTITIES = '/appDiscovery/applications/{0}/identities?limit={1}&offset={2}&timezone={3}'
    APP_RISK = '/appDiscovery/applications/{0}/risk?timezone={1}'
    SEARCH_APP_COUNT = '/appDiscovery/applications?timezone={0}&{1}'
    CHANGE_APP_LABLE = '/appDiscovery/applications/{}'


class InvestigateAPIS(Enum):
    """Enum representation for Investigate Api endpoints"""

    DOMAIN_URIS = {"domain_status_categorization": ['/investigate/v2/domains/categorization/{}?showLabels]'],
                   "domain_volume": ['/investigate/v2/domains/volume/{}'],
                   "cooccurrences_domain": ['/investigate/v2/recommendations/name/{}.json'],
                   "passive_dns": ['/investigate/v2/pdns/name/{}', '/investigate/v2/pdns/domain/{}'],
                   "related_domains": ['/investigate/v2/links/name/{}'],
                   "security_information": ['/investigate/v2/security/name/{}', '/investigate/v2/domains/risk-score/{}'],
                   "whois_information": ['/investigate/v2/whois/{}'],
                   "threat_grid_integration": ['/investigate/v2/samples/{}']}

    IP_URIS = {"passive_dns": ['/investigate/v2/pdns/ip/{}'],
               "as_information": ['/investigate/v2/bgp_routes/ip/{}/as_for_ip.json'],
               "threat_grid_integration": ['/investigate/v2/samples/{}']}

    HASH_URIS = {"threat_grid_integration": ['/investigate/v2/sample/{}', '/investigate/v2/sample/{}/connections']}

    URL_URIS = {"threat_grid_integration": ['/investigate/v2/samples/{}']}

    TOP_MILLION ='/investigate/v2/topmillion?limit=2'


class ProcessInvestigateAPIs(Enum):
    """Enum representation for mapping Investigate Api endpoints to the respestive process function"""

    PROCESS_METHODS = {"domain_status_categorization": 'process_categorization',
                       "domain_volume": 'process_domain_volume',
                       "cooccurrences_domain": 'process_cooccurance',
                       "passive_dns": 'process_pdns',
                       "related_domains": 'process_related',
                       "security_information": 'process_security_info',
                       "whois_information": 'process_whois_info',
                       "threat_grid_integration": 'process_threat_grid',
                       "as_information": 'process_as_info'}


class Collections(Enum):
    """Enum representation for KV store collection"""

    COLLECTION = {'domain': "cisco_investigate_domains",
                  'ip': "cisco_investigate_ips",
                  'hash': "cisco_investigate_hashes",
                  'url': "cisco_investigate_urls"}


class DestinationListAPIEndpoints(Enum):
    """Enum representation for destination list api endpoints"""

    GET_DESTINATION_LISTS = '/policies/v2/destinationlists'
    BLOCK_DESTINATION = '/policies/v2/destinationlists/{}/destinations'
    FETCH_ALL_DESTINATIONS = '/policies/v2/destinationlists/{}/destinations'
    REMOVE_DESTINATION = '/policies/v2/destinationlists/{}/destinations/remove'


class AlertActionType(Enum):
    """Enum representation for alert action types"""

    BLOCK_DESTINATIONS = "block_destinations"
    INVESTIGATE_DESTINATIONS = "investigate_destinations"
    INVESTIGATE_REPORTS = "investigate_reports"


class ModInputType(Enum):
    """Enum representation for modular input types"""

    APP_DISCOVERY = "app_discovery"
    PRIVATE_APPS = "private_apps"
    CLOUDLOCK = "cloudlock"
    CLOUDLOCK_HEALTH_CHECK = "cloudlock_health_check"
    DESTINATION_LISTS_HEALTH_CHECK = "destination_lists_health_check"
    INVESTIGATE_HEALTH_CHECK = "investigate_health_check"
    ALERT_DASHBOARD_INDEX = "alert_dashboard_index"

class ModInputInterval(Enum):
    """Enum representation for modular input intervals"""

    APP_DISCOVERY = 14400
    PRIVATE_APPS = 14400
    CLOUDLOCK = 300
    CLOUDLOCK_HEALTH_CHECK = 1440
    DESTINATION_LISTS_HEALTH_CHECK = 1440
    INVESTIGATE_HEALTH_CHECK = 1440
    ALERT_DASHBOARD_INDEX = 14400


class DLPReportingAPIEndpoints(Enum):
    """Enum representation for DLP Reporting API endpoints.

    Base URL: https://api.sse.cisco.com/reports.{region}/v2
    OAuth Scope: reports.dlp:read
    """

    REALTIME_EVENTS = '/dlp/realTime/events?from={0}&to={1}&limit={2}&offset={3}'
    SAAS_API_EVENTS = '/dlp/saasApi/events?from={0}&to={1}&limit={2}&offset={3}'
    AI_GUARDRAILS_EVENTS = '/dlp/aiGuardrails/events?from={0}&to={1}&limit={2}&offset={3}'
    EVENT_DETAILS = '/dlp/{0}/events/{1}'
    IDENTITIES = '/identities?limit={0}'

@dataclass
class ModularInputConfig:
    """Dataclass for modular input configuration"""

    interval: Optional[int] = None
    index: Optional[str] = None
    log_level: Optional[str] = None
    org_id: Optional[str] = None
    time_window: Optional[int] = None

    def to_splunk_params(self):
        params = {}
        if self.interval is not None:
            params["interval"] = self.interval
        if self.index is not None:
            params["index"] = self.index
        if self.log_level is not None:
            params["Log_Level"] = self.log_level
        if self.org_id is not None:
            params["org_id"] = self.org_id
        if self.time_window is not None:
            params["time_window"] = self.time_window
        return params
