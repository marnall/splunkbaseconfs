HOST = "https://bifrost.cyble.ai/engine/api/v1" # api-engine base url
ALERT_URL = "/y/tpi/splunk/alerts"
IOC_URL = "https://api.cyble.ai/engine/api/v4/y/iocs"
ALERTS_USERNAME = "Alerts"
IOCV2_USERNAME = "IOC"
MASK = "*********************"
DEFAULT_REQUEST_TIMEOUT = 10 * 60
PAYLOAD_ALERTS = lambda gte, lte, is_count=False, skip=0, take=1000, service= "", hide_data=True : {
    "filters": {
        "service": [service],
        "created_at": {
            "gte": gte.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "lte": lte.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        },
        "status": [ "VIEWED", "UNREVIEWED", "CONFIRMED_INCIDENT", "UNDER_REVIEW", "INFORMATIONAL" ]
    },
    "orderBy": [{ "created_at": "desc" }],
    "skip": skip,
    "take": take,
    "countOnly": is_count,
    "taggedAlert" : False,
    "withDataMessage": True,
    "hide_data": hide_data
}

PAYLOAD_VALIDATE = {
    "orderBy": [{"created_at": "desc"}],
    "skip": 0,
    "take": 1,
    "filters": {
        "created_at": {
            "gte": "2022-06-01T18:30:00.000Z",
            "lte": "2022-06-01T18:30:00.000Z"
        },
    },
    "countOnly": False,
    "taggedAlert" : False,
    "withDataMessage": True,
    "hide_data": True
}


HEADERS = lambda alerts_api_key: {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {alerts_api_key}"
}

ENCODED_HEADER = lambda headers: {k: v.encode('utf-8') for k, v in headers.items()}

HEADERS_IOC = lambda ioc_api_key: {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {ioc_api_key}"
}

PARAMETERS_IOC = lambda page, gte, lte: {
    "page": page,
    "startDate": gte.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "endDate": lte.strftime("%Y-%m-%dT%H:%M:%SZ")
}


MIN_MINUTES_TO_FETCH = 30 # minimum number of minutes to fetch
DATA_PAR_PAGE = 100 # number of data to fetch per page
MAX_CUNCURRENT_REQUESTS = 1 # maximum number of concurrent requests to api-engine
MAX_ALLOWED_DAYS = 15 # maximum number of days to fetch in initial setup