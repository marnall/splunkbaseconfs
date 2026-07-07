# constants.py

XSOAR_WIDGETS_API_ENDPOINT = "statistics/widgets/query"
APP_NAME = "cortex-xsoar-analytics"

HOST = "localhost"
PORT = 8089

SYSTEM_TOKEN_CONF_DETAILS = {
    "conf_file": "system-token.conf",
    "stanza_name": "api-token",
    "setting": "value"
    }

CORTEX_XSOAR_ANALYTICS_CONF_DETAILS = {
    "conf_file": "cortex-xsoar-analytics.conf",
    "stanza_name": "incident_widget_endpoint",
    "setting": "verify_ssl"
    }

WIDGET_CONFIG = {
    'Cache': None, 
    'packName': '', 
    'dataType': 'incidents', 
    'itemVersion': '', 
    'sizeInBytes': 0, 
    'params': {
        'showGraphValues': True, 
        'tableColumns': []
          }, 
    'query': '', 
    'created': '0001-01-01T00:00:00Z', 
    'modified': '0001-01-01T00:00:00Z', 
    'shouldCommit': False, 
    'fromServerVersion': '', 
    'propagationLabels': ['all'], 
    'name': 'All Incidents', 
    'definitionId': '', 
    'vcShouldKeepItemLegacyProdMachine': False, 
    'dateRange': {
        'fromDate': '0001-01-01T00:00:00Z', 
        'toDate': '0001-01-01T00:00:00Z', 
        'period': {
            'by': '', 
            'byTo': 'days', 
            'byFrom': 'days', 
            'toValue': 0, 
            'fromValue': 10000, 
            'field': ''
            }, 
        'fromDateLicense': '0001-01-01T00:00:00Z'
        }, 
    'commitMessage': '', 
    'isPredefined': False, 
    'vcShouldIgnore': False, 
    'packID': '', 
    'toServerVersion': '', 
    'cacheVersn': 0, 
    'category': '', 
    'prevName': 'All Incidents', 
    'widgetType': 'table', 
    'customCalculation': {
        'operation': 'count', 
        'fieldName': '', 
        'expression': ''
        },
    "size": 200000000
  }
