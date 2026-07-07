"""Constants module for the XM Cyber Splunk app.

This module contains various constant values used throughout the XM Cyber Splunk app.
These constants include API endpoints, authentication types, timeouts, and other
configuration parameters.
"""

PROTOCOL = "https"
VERIFY = True
API_REQUEST_TIMEOUT = 120
STATUS_FORCELIST = list(range(500, 600)) + [429]
AUTH_TYPE_OAUTH = "oauth"
OAUTH_PREFIX = "Bearer"
BASIC_AUTH_KEY = "XM_JWT"
OAUTH_ENDPOINT = "/api/auth/"
REGENERATE_TOKEN_ENDPOINT = "/api/refresh-token/"
REGENERATE_TOKEN = ""
ALL_ENTITIES_ENDPOINT = "/api/v2/reports/data/scenariosCriticalAssetsReport/entities"
ALL_INVENTORY_ENTITIES_ENDPOINT = "/api/entityInventory/entities"
CHOKEPOINT_ENDPOINT = "/api/v2/reports/data/scenariosChokePointsReport/chokePointsEntities"
GET_SENSORS_ENDPOINT = "/api/sensors"
GET_SCENARIOS_ENDPOINT = "/api/scenarios/v2/scenarios"
GET_SECURITY_RISK_SCORE_ENDPOINT = "/api/scenarios/v2/scenarios/riskScore"
GET_FINDINGS_EXPOSURES_ENDPOINT = "/api/v2/reports/data/scenariosExposureReport/exposures"
GET_AUDIT_TRAIL_ENDPOINT = "/api/audit-trail/auditRecords"
GET_DEVICES_ENDPOINT = "/api/v2/vavm/devices"
GET_PRODUCTS_ENDPOINT = "/api/v2/vavm/public/products"
GET_VULNERABILITIES_ENDPOINT = "/api/v2/vavm/public/vulnerabilities/"
DEVICES_SOURCETYPE = "xmcyber:devices"
PRODUCTS_SOURCETYPE = "xmcyber:products"
VULNERABILITIES_SOURCETYPE = "xmcyber:vulnerabilities"
RISKSCORE_SCENARIO_SOURCETYPE = "xmcyber:riskscore:scenario"
SENSATIVE_DATA = ["Authorization", "x-api-key", "refreshToken"]
CHOKEPOINT_COUNT_SOURCETYPE = "xmcyber:chokepoint:stats"
PAGE_SIZE = 1000
DEVICES_PAGE_SIZE = 5000
VRM_PAGE_SIZE = 100
AUTH_ERROR_MESSAGE = (
    "{service_name} with account {account} using basic authentication is not supported. "
    "Please use account with OAuth authentication."
)
