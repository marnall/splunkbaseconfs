"""
This file contains CrowdStrike endpoints that are used in the add-on.
"""

FALCON_URL = "https://falconapi.crowdstrike.com/"
UPLOAD_IOC = "indicators/entities/iocs/v1"
CHANGE_DETECTION_STATE = "detects/entities/detects/v2"
GET_DEVICE_IDS_ASSOCIATED_WITH_IOC = "threatgraph/combined/ran-on/v1"
GET_DEVICE_COUNTS_ASSOCIATED_WITH_IOC = "indicators/aggregates/devices-count/v1"
INDICATOR_QUERY_ENDPOINT = "/indicators/queries/iocs/v1?include_deleted=true"
DEVICE_QUERY_ENDPOINT = "/devices/queries/devices/v1"
DETECT_QUERY_ENDPOINT = "/detects/queries/detects/v1"
DATA_QUERY_ENDPOINTS = [INDICATOR_QUERY_ENDPOINT, DEVICE_QUERY_ENDPOINT, DETECT_QUERY_ENDPOINT]
INDICATOR_ENTITY_ENDPOINT = "/indicators/entities/iocs/v1{?ids*}"
DEVICE_ENTITY_ENDPOINT = "/devices/entities/devices/v1"
DETECT_ENTITY_ENDPOINT = "/detects/entities/summaries/GET/v1"
GET_DEVICE_IDS_USING_FILTER = "/devices/queries/devices/v1"
