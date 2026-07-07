APP_FOLDER_NAME = 'relay-module'

API_RESPONSE_HEADERS = {
    'Content-Type': 'application/json'
}
DEFAULT_SPLUNK_API_PORT = '8089'
SPLUNK_API_URI_TEMPLATE = 'https://localhost:{port}/services'
DEFAULT_SPLUNK_HOST = '127.0.0.1'
SPLUNK_INSTANCE_CONFIG_FILE = 'instance.cfg'
SPLUNK_INSTANCE_CONFIG_FOLDER = 'etc'

SSE_CONNECTOR_FOLDER = 'connector'
SSE_CONNECTOR_FILE = 'connector'
SSE_CONNECTOR_CONFIG_FOLDER = 'conf'
SSE_CONNECTOR_CONFIG_FILE = 'config.toml'
SSE_CONNECTOR_CERT_FOLDER = 'certs'
SSE_CONNECTOR_DATA_FOLDER = 'data'
SSE_CONNECTOR_ROOT_CERT_FILE = 'root.cert'
SSE_CONNECTOR_RUNNING_COMMAND = 'server'
SSE_CONNECTOR_CONF_ARG = '-c'
DEFAULT_SSE_CONNECTOR_PORT = '8080'

CONFIG_PORT_REGEX = 'server_port = ([\d]+)\n'

SSE_API_URL = 'http://localhost:{port}/{version}'
SSE_FQDN_DEFAULT_DOMAIN = 'api-sse.cisco.com'
SSE_CONNECTOR_CONTEXT_BODY = {
    'clientInfo': {
        'version': '1.0',
        'description': 'Cisco SecureX threat response: Relay module',
        'name': 'Cisco SecureX threat response: Relay module',
        'guid': '',
        'type': 'Relay module',
        'ip': DEFAULT_SPLUNK_HOST
    },
    'settings': {
        'client': {
            'administration': {
                'auth': {},
                'uri': SPLUNK_API_URI_TEMPLATE.format(
                    port=DEFAULT_SPLUNK_API_PORT)
            }
        },
        'exchange': {
            'registration': {
                'refreshInterval': 1200
            },
            'fqdn': SSE_FQDN_DEFAULT_DOMAIN
        }
    }
}
