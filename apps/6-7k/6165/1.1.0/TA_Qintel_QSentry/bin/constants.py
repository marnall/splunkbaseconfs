import re

VERSION = '1.0.0'
UA = 'Qintel QSentry Splunk Add-on {}'.format(VERSION)

APP_NAME = 'TA_Qintel_QSentry'

QSENTRY_BATCH_SIZE = 10  # this should not exceed KV_BATCH_SIZE
QSENTRY_POOL_SIZE = 5

INTEL_KEYS = ['last_seen', 'tags', 'asn', 'asn_name', 'score',
              'descriptions']

CACHE_LIMIT = 2  # hours
MAX_CACHE_LIMIT = 12  # hours

QSENTRY_KV_STORE = 'qintel_qsentry_cache'

KV_RBATCH_SIZE = 1000  # defaults 1000 in limits.conf
KV_WBATCH_SIZE = 1000  # defaults 1000 in limits.conf

SEARCH_TIMEOUT = 10

RE_IPV4 = re.compile(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(\d{1,3})$')
RE_IPV6 = re.compile(r'(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))')
RE_IP = [RE_IPV4, RE_IPV6]

ENRICHMENT_ERROR = 'Qintel enrichment error occurred'

REALM = f'__REST_CREDENTIAL__#{APP_NAME}#configs/conf-qintel_qsentry_settings'
CONFIG_FILE = 'qintel_qsentry_settings'