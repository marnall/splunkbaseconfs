"""File with constants used in integration."""

THOUSANDEYES_BASE_URL = "https://api.thousandeyes.com/v7"
THOUSANDEYES_AUTH_ENDPOINT = "/oauth2/device/authorization"
THOUSANDEYES_TOKEN_API_ENDPOINT = "/oauth2/token"
THOUSANDEYES_CURRENT_USER_ENDPOINT = "/users/current"
THOUSANDEYES_CREATE_STREAM = "/stream"
THOUSANDEYES_ACC_GROUP_ENDPOINT = "/account-groups"
THOUSANDEYES_CEA_TEST_ENDPOINT = "/tests"
THOUSANDEYES_ENDPOINT_SCHEDULED_TEST_ENDPOINT = "/endpoint/tests/scheduled-tests"
THOUSANDEYES_ENDPOINT_DYNAMIC_TEST_ENDPOINT = "/endpoint/tests/dynamic-tests/agent-to-server"
THOUSANDEYES_INGEST_ENDPOINT = "/ingest/events/itsi"
THOUSANDEYES_TAGS_ENDPOINT = "/tags"
TAGS_EXPAND_ASSIGNMENTS = "assignments"
CLIENT_ID = "0oalgciz1dyS1Uonr697"
AUTH_SCOPE = "organization:read offline_access tests:read endpoint-tests:read streams:manage alerts:manage tags:read integrations:manage"
GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"
REGENERATE_GRANT_TYPE = "refresh_token"
HEADER_AUTH_PREFIX = "Bearer"
VERIFY_SSL = True
REQUEST_TIMEOUT = 120
THOUSANDEYES_CEA_PATH_INFO_URL = "{}/test-results/{}/path-vis"
THOUSANDEYES_ENDPOINT_SCHEDULED_PATH_INFO_URL = (
    "{}/endpoint/test-results/scheduled-tests/{}/path-vis"
)
THOUSANDEYES_ENDPOINT_DYNAMIC_PATH_INFO_URL = (
    "{}/endpoint/test-results/dynamic-tests/{}/path-vis"
)
THOUSANDEYES_EVENT_URL = "{}/events"
THOUSANDEYES_ACTIVITY_URL = "{}/audit-user-events"
THOUSANDEYES_ALERTS_ENDPOINT = "/alerts"
THOUSANDEYES_ALERTS_RULES_ENDPOINT = "/alerts/rules"
THOUSANDEYES_WEBHOOKS_OPERATIONS_ENDPOINT = "/operations/webhooks"
THOUSANDEYES_CONNECTORS_ENDPOINT = "/connectors/generic"

# Common source for all data types
THOUSANDEYES_SOURCE = "cisco:thousandeyes:stream"

# Stream Metrics constants
METRIC_SOURCE = THOUSANDEYES_SOURCE
METRIC_SOURCETYPE = "cisco:thousandeyes:metric"

# Trace constants
TRACE_SOURCE = THOUSANDEYES_SOURCE
TRACE_SOURCETYPE = "cisco:thousandeyes:trace"

# Path visualization constants
PATH_VIS_SOURCE = THOUSANDEYES_SOURCE
PATH_VIS_SOURCETYPE = "cisco:thousandeyes:path-vis"

# Account group constant
ACCOUNT_GROUP_SOURCETYPE = "cisco:thousandeyes:account-group"

THOUSANDEYES_STREAM_PAYLOAD = {
    "type": "splunk-hec",
    "signal": "metric",
    "endpointType": "http",
    "streamEndpointUrl": "",
    "dataModelVersion": "v2",
    "tagMatch": [],
    "testMatch": [],
    "exporterConfig": {
        "splunkHec": {
            "index": "",
            "sourceType": METRIC_SOURCETYPE,
            "source": METRIC_SOURCE,
            "token": "",
        }
    },
}

THOUSANDEYES_TRACE_PAYLOAD = {
    "type": "splunk-hec",
    "signal": "trace",
    "endpointType": "http",
    "streamEndpointUrl": "",
    "dataModelVersion": "v2",
    "tagMatch": [],
    "testMatch": [],
    "exporterConfig": {
        "splunkHec": {
            "index": "",
            "sourceType": TRACE_SOURCETYPE,
            "source": TRACE_SOURCE,
            "token": "",
        }
    },
}

SPLUNK_CLOUD_HEC_PORT = 443
CEA_TEST_TYPES = [
    "agent-to-agent",
    "agent-to-server",
    "bgp",
    "http-server",
    "page-load",
    "web-transactions",
    "ftp-server",
    "dns-server",
    "dns-trace",
    "dns-dnssec",
    "sip-server",
    "voice",
    "api",
]
CEA_TEST_TYPES_FOR_METRICS = CEA_TEST_TYPES  # All CEA test types for metrics

CEA_TEST_TYPES_FOR_TRACES = [
    "page-load",
    "web-transactions",
    "api",
]
ENDPOINT_TEST_TYPES = ["agent-to-server", "http-server"]
DEFAULT_ENDPOINT_DYNAMIC_TEST_TYPE = "agent-to-server"
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
ENTERPRISE_HEC_STREAM_URL = "https://{}:{}/services/collector/event"
CLOUD_HEC_STREAM_URL = "https://http-inputs-{}.splunkcloud.com:{}/services/collector/event"
LOCAL_FOLDER = "local"
CERT_FOLDER = "certificates"
PROXY_CERT_FILE_NAME = "proxy_cert.pem"
THOUSANDEYES_TA_NAME = "ta_cisco_thousandeyes"
LOCAL_HOSTNAMES = ["localhost", "127.0.0.1", "::1", ""]

SEVERITY_MAPPING = {
                "1": "Info",
                "2": "Normal",
                "3": "Low",
                "4": "Medium",
                "5": "High",
                "6": "Critical",
                "info": "Info",
                "normal": "Normal",
                "low": "Low",
                "medium": "Medium",
                "high": "High",
                "critical": "Critical"
            }

# Activity logs constants
ACTIVITY_LOGS_SOURCE = THOUSANDEYES_SOURCE
ACTIVITY_LOGS_SOURCETYPE = "cisco:thousandeyes:activity"

THOUSANDEYES_ACTIVITY_LOGS_PAYLOAD = {
    "type": "splunk-hec",
    "signal": "log",
    "endpointType": "http",
    "streamEndpointUrl": "",
    "dataModelVersion": "v2",
    "testMatch": [],
    "exporterConfig": {
        "splunkHec": {
            "index": "",
            "sourceType": ACTIVITY_LOGS_SOURCETYPE,
            "source": ACTIVITY_LOGS_SOURCE,
            "token": "",
        }
    },
}

# Webhook payload template for alerts
THOUSANDEYES_WEBHOOK_PAYLOAD_TEMPLATE = """{
    "sourcetype": "cisco:thousandeyes:alerts",
    "source": "cisco:thousandeyes:webhook",
    "index": "alerts_index",
    "event": {
        "eventId": "{{id}}-{{alert.id}}",
        "eventType": "THOUSANDEYES_ALERT_NOTIFICATION",
        "id": "{{id}}",
        "type": "{{type.id}}",
        "accountId": "{{alert.rule.account.id}}",
        "orgId": "{{alert.rule.account.organization.id}}",
        {{#if alert.test}}
        "testId": "{{alert.test.id}}",
        "thousandeyes_test_id": "{{alert.test.id}}",
        "test_description": "{{alert.test.description}}",
        "test_type":"{{alert.test.testType}}",
        "itsiDrilldownURI":"https://app.thousandeyes.com/network-app-synthetics/views/?__a={{alert.rule.account.id}}&testId={{alert.test.id}}",
        {{/if}}
        "severity_id": "{{#if (eq alert.severity.id 'INFO')}}1{{/if}}{{#if (eq alert.severity.id 'MINOR')}}3{{/if}}{{#if (eq alert.severity.id 'MAJOR')}}5{{/if}}{{#if (eq alert.severity.id 'CRITICAL')}}6{{/if}}",
        "vendor_severity": "{{alert.severity.id}}",
        "app": "THOUSANDEYES",
        {{#if alert.targets.size}}
        "src": "{{#each alert.targets}}{{#if @first}}{{description}}{{/if}}{{/each}}",
        {{/if}}
        "signature":"{{alert.rule.name}}",
        "alert_type":"{{alert.rule.alertType.id}}",
        "alert": {
            "id": "{{alert.id}}",
            "type": "{{alert.rule.alertType.id}}",
            "severity": "{{alert.severity.id}}",
            {{#if alert.test}}
            "test": {
                "name": "{{alert.test.name}}"
            },
            "targets": [
                {{#each alert.targets}}
                "{{description}}"{{#unless @last}}, {{/unless}}
                {{/each}}
            ],
            {{/if}}
            {{#with alert.rule as | rule |}}
            "rule": {
                "id": "{{rule.id}}",
                "name": "{{rule.name}}",
                "expression": "{{formatExpression rule.expression}}",
                "notes": "{{rule.notes}}"
            },
            {{/with}}
            "triggered": {{alert.firstSeen.epochMilli}},
            {{#if alert.timeCleared}}
            "cleared": {{alert.timeCleared.epochMilli}},
            {{/if}}
            "details": [
                {{#each alert.details}}
                    {
                        "metricsAtStart" : "{{metricsAtStart}}",
                        {{#if metricsAtEnd}}
                        "metricsAtEnd" : "{{metricsAtEnd}}",
                        {{/if}}
                        "source" : {
                            "id": "{{source.id}}",
                            "name": "{{source.name}}"
                            {{#if source.asn}}
                            , "asn": "{{source.asn.name}}"
                            {{/if}}
                        }
                    }
                    {{#unless @last}}, {{/unless}}
                {{/each}}
            ]
        }
    }
}"""
