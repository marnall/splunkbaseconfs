import pytz

PST = pytz.timezone('America/Los_Angeles')
SSL_VERIFY = True
EVENTS_URL = "https://ws.riskiq.net/v1/event/search?&scroll&sort=updatedAt&order=ASC"
GLOBAL_INVENTORY_ASSETS_URL = "https://api.riskiq.net/v1/globalinventory/search"
GET_CVE_URL = "https://cve.mitre.org/data/downloads/allitems.csv"
ACCOUNT_CONF_NAME = "ta_riskiq_account"
GLOBAL_INVENTORY_ASSETS_SOURCE = "riskiq_globalinventory_assets"
