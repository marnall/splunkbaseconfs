import re

VERSION = '1.1.0-dev'
UA = 'Qintel PMI Splunk add-on {}'.format(VERSION)

APP_NAME = 'TA_Qintel_PMI'

CACHE_LIMIT = 2  # hours
MAX_CACHE_LIMIT = 12  # hours

PMI_KV_STORE = 'qintel_pmi_cache'

KV_RBATCH_SIZE = 1000  # defaults 1000 in limits.conf
KV_WBATCH_SIZE = 1000  # defaults 1000 in limits.conf

SEARCH_TIMEOUT = 10

RE_FULL_CVE = re.compile(r'^CVE-\d{4}-\d{4,7}$', re.IGNORECASE)
RE_CVE = [RE_FULL_CVE]

ENRICHMENT_ERROR = 'Qintel enrichment error occurred'

REALM = f'__REST_CREDENTIAL__#{APP_NAME}#configs/conf-qintel_pmi_settings'
CONFIG_FILE = 'qintel_pmi_settings'