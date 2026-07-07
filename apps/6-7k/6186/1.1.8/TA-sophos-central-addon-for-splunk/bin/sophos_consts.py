from splunk.clilib import cli_common as cli
from unittest.mock import MagicMock

sophos_configs = cli.getConfStanza(
    'ta_sophos_central_addon_for_splunk_settings', 'additional_parameters'
)

if sophos_configs.get('region') == "dev":
    AUTH_BASE_URL = "dev-id.sophos.com"
    WHO_AM_I_BASE_URL = "api.dev.central.sophos.com"
elif sophos_configs.get('region') == "qa":
    AUTH_BASE_URL = "test-id.sophos.com"
    WHO_AM_I_BASE_URL = "api.qa.central.sophos.com"
elif sophos_configs.get('region') == "prod":
    AUTH_BASE_URL = "id.sophos.com"
    WHO_AM_I_BASE_URL = "api.central.sophos.com"
else:
    if not (isinstance(sophos_configs, MagicMock)):
        raise Exception("No region is configured.")
    else:
        AUTH_BASE_URL = ""
        WHO_AM_I_BASE_URL = ""

# API Endpoints
ALERT_ENDPOINT = "/common/v1/alerts"
AUTH_ENDPOINT = "/api/v2/oauth2/token"
ENDPOINT_ENDPOINT = "/endpoint/v1/endpoints"
EVENT_ENDPOINT = "/siem/v1/events"
ORGANIZATION_TENANT_ENDPOINT = "/organization/v1/tenants"
PARTNER_TENANT_ENDPOINT = "/partner/v1/tenants"
WHO_AM_I_ENDPOINT = "/whoami/v1"

# Global variables
CONNECT_TIMEOUT = 15
GLOBAL_RETRY = 1
READ_TIMEOUT = 120
LIMIT = 1000

# Sophos token lock timeout in seconds
LOCK_POLLING_INTERVAL = 10
LOCK_TIMEOUT = 50

# Rest call consts
USER_AGENT = "Sophos Central Splunk Addon 1.1.8"
