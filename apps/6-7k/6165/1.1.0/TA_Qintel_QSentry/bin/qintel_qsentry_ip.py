from multiprocessing.dummy import Pool as ThreadPool
from json import dumps
from utils import get_config_item, KVStore, get_token
from constants import UA, QSENTRY_KV_STORE, QSENTRY_BATCH_SIZE, \
    QSENTRY_POOL_SIZE, INTEL_KEYS

from solnlib.credentials import CredentialNotExistException

from qintel_helper import search_qsentry

THREAT_MAP = {
    'tags': set(),
    'last_at': set(),
    'first_at': set(),
    'provider': set()
}


class QintelQSentryIP(object):

    def __init__(self, session_key, logger, field):

        self.session_key = session_key
        self.logger = logger
        self.field = field

        self.kvstore = KVStore(self.session_key, self.logger, QSENTRY_KV_STORE)

    def _init_qauth(self):

        QSENTRY_API_URL \
            = get_config_item(self.session_key, 'qsentry', 'qsentry_api_url')
        if not QSENTRY_API_URL or QSENTRY_API_URL == '':
            QSENTRY_API_URL = None

        try:
            QSENTRY_API_KEY = get_token(self.session_key, 'qsentry', 'qsentry_api_key')
        except CredentialNotExistException:
            QSENTRY_API_KEY = None

        if not QSENTRY_API_KEY:
            raise RuntimeError('missing QSentry API Token. '
                                   'Please configure the App appropriately.')

        self.search_args = {
            'remote': QSENTRY_API_URL,
            'token': QSENTRY_API_KEY,
            'user_agent': UA,
            'logger': self.logger.error
        }

    def _query_qsentry(self, selector_batch):
        self.logger.debug(f'url is: {self.search_args["remote"]}')
        self.logger.debug(f"data is: {dumps(selector_batch).encode('utf-8')}")

        qsentry_data = {}
        for each in selector_batch:

            try:
                qsentry_data[each] = search_qsentry(each, **self.search_args)
            except Exception as e:
                self.logger.error(f'API request failed, error: {str(e)}'
                                  f', ip: {each}')
                return qsentry_data

        return qsentry_data

    def _fetch_qsentry_data(self, selectors, ip_results):

        batches = [selectors[i:i + QSENTRY_BATCH_SIZE]
                   for i in range(0, len(selectors), QSENTRY_BATCH_SIZE)]

        pool = ThreadPool(QSENTRY_POOL_SIZE)
        lookup = lambda selector_batch: self._query_qsentry(selector_batch)
        qsentry_results = pool.map(lookup, batches)

        for r in qsentry_results:
            for ip, data in r.items():
                ip_results[ip] = data

        self.kvstore.write_cache(qsentry_results)

    def _format_qsentry_data(self, ip_result, event_time):

        return_data = {}

        for k in INTEL_KEYS:
            return_data[f'qintel_{k}'] = ip_result.get(k)

        return return_data

    def _generate_ip_results(self, event, ip_results):

        event_ip = event.get(self.field)
        event_time = float(event.get('_time'))
        fields = {}

        fields = self._format_qsentry_data(ip_results.get(event_ip, {}),
                                            event_time)

        self.logger.debug(f'event_output={event_ip}: {fields}')

        for k, v in fields.items():
            event[k] = v

        return event

    def enrich(self, events, selectors):

        ip_results = {}
        self.kvstore.query_cache(selectors, ip_results)

        if len(selectors) > 0:
            self._init_qauth()
            self._fetch_qsentry_data(selectors, ip_results)

        for e in events:
            yield self._generate_ip_results(e, ip_results)
