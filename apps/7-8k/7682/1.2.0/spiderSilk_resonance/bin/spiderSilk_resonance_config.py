ADDON_NAME = "spiderSilk_resonance"

HTTP_CLIENT_EXTRA_HEADERS = {"Client": "spiderSilk Resonance Splunk Addon"}

# External API Configuration
APIS_TO_CRAWL = {
    "threats": {
        "api_base_url": "https://api.spidersilk.com/client/v1/threats",
        "uniqueID": "uuid",
        "activeKey": "state",
        "NotActiveKeyValue": "Closed",
        "limit": 100
    },
    "darkweb": {
        "api_base_url": "https://api.spidersilk.com/client/v1/darkweb",
        "uniqueID": "uuid",
        "activeKey": "status",
        "NotActiveKeyValue": "Closed",
        "limit": 100
    },
    "assets": {
        "api_base_url": "https://api.spidersilk.com/client/v1/assets",
        "uniqueID": "asset_id",
        "activeKey": "placeholder",
        "NotActiveKeyValue": "placeholder",
        "limit": 100
    }
}

MAX_APP_LOCK_DURATION_HOURS = 3
