"""Configurations for Authentic8"""

FIELDS = [
    'authentic8_api_url',
    'auth_token',
    'private_key',
    'organization_name',
    'log_type'

]


log_type_list = [
    "A8SS", "ADMIN_AUDIT", "APP_LAUNCH", "AUTH", "BLOCKED URL",
    "CASE MANAGER", "CLIPBOARD", "COOKIES", "DOWNLOAD", "ENC",
    "EVENT", "EXPLOIT", "EXTENSION", "HARVEST", "ISOLATE_BYPASS",
    "LAUNCHER", "LOCATION CHANGE", "POST DATA", "PRINT", "SESSION",
    "SMS", "TRAFFICMAN", "TRANSLATION", "UPLOAD", "URL",
]

# Log type update settings
LOG_TYPE_UPDATE_INTERVAL_SECONDS = 86400  # 24 hours
LOG_TYPE_CHECKPOINT_KEY = "log_type_list_updated"
LOG_TYPE_MIN_COUNT = 20  # Sanity threshold for API response


cim_map_dict = {'client_ip': 'src', 'method': 'http_method',
                'path': 'uri_path', 'response_code': 'status',
                'url': 'url', 'username': 'user', 'query': 'uri_query',
                'bytes': 'bytes', 'action': 'action',
                'audit_type': 'signature', 'micro_category': 'category',
                'exploit_name': 'file_name', 'destination_path': 'uri_path'}
