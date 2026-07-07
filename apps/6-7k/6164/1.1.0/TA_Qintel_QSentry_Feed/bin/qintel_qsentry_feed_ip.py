from utils import KVStore
from constants import FEED_KV_STORE
from collections import defaultdict
from copy import deepcopy

RETURN_STRUCT = {
    'qintel_tags': set(),
    'qintel_descriptions': set()
}


class QintelQSentryIP(object):

    def __init__(self, session_key, logger, field):

        self.session_key = session_key
        self.logger = logger
        self.field = field

        self.feed_kvstore = KVStore(self.session_key, self.logger,
                                    FEED_KV_STORE)

    def _fetch_feed_data(self, selectors):

        ip_results = defaultdict(lambda: deepcopy(RETURN_STRUCT))

        feed_results = self.feed_kvstore.bulk_read('ip_address', selectors)

        for record_set in feed_results:    
            for r in record_set:

                ip = r['ip_address']
                for k in RETURN_STRUCT.keys():
                    value = r.get(k)
                    if isinstance(value, list):
                        ip_results[ip][k].update(value)

                    if isinstance(value, str):
                        ip_results[ip][k].add(value)

        return ip_results

    def _generate_ip_results(self, event, ip_results):
        event_ip = event.get(self.field)
        ip_result = ip_results.get(event_ip, {})

        for k in RETURN_STRUCT.keys():
            value = ip_result.get(k)
            if value:
                event[k] = list(ip_result[k])
            else:
                event[k] = None

        return event

    def enrich(self, events, selectors):

        ip_results = self._fetch_feed_data(selectors)

        for e in events:
            yield self._generate_ip_results(e, ip_results)
