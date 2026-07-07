import arrow
from multiprocessing.dummy import Pool as ThreadPool

from utils import get_config_item, get_crosslink_credentials, \
    extract_json_values, KVStore
from constants import UA, PMI_KV_STORE

from solnlib.credentials import CredentialNotExistException

from qintel_helper import search_pmi

class QintelCVE(object):

    def __init__(self, session_key, logger, field):

        self.session_key = session_key
        self.logger = logger
        self.field = field
        self.kvstore = KVStore(self.session_key, self.logger, PMI_KV_STORE)

    def _init_client(self):

        remote = get_config_item(self.session_key, 'pmi', 'pmi_api_url')
        if not remote or remote == '':
            remote = None

        try:
            user, secret = get_crosslink_credentials(self.session_key)
        except CredentialNotExistException:
            user, secret = None, None

        if not user or not secret:
            raise RuntimeError('Missing Crosslink credenials. '
                               'Please configure App.')

        self.search_args = {
            'remote': remote,
            'client_id': user,
            'client_secret': secret,
            'user_agent': UA,
            'logger': self.logger.warn
        }

    def _lookup_cve(self, cve):

        try:
            result = search_pmi(cve, 'cve', **self.search_args)
        except Exception as e:
            self.logger.exception(f'cve search failed {str(e)}')
            return

        return {cve: result.get('data')}

    def _format_cve_data(self, data):

        return_data = {}
        notes = []
        ts = []

        # actors, types, affected system, patches
        return_data['qintel_cve_actors'] = list(set(
            extract_json_values(data, 'label')))
        return_data['qintel_cve_actor_types'] = list(set(
            extract_json_values(data, 'tag_type')))
        return_data['qintel_cve_affected_system'] = list(set(
            extract_json_values(data, 'name')))
        return_data['qintel_cve_affected_version'] = list(set(
            extract_json_values(data, 'versions')))
        return_data['qintel_cve_patches'] = list(set(
            extract_json_values(data, 'patches')))

        # exploits, notes
        return_data['qintel_cve_exploit_types'] = list(set(
            extract_json_values(data, 'exploit_type'))
        )

        # timestamps
        timestamp_data = extract_json_values(data, 'timestamps')
        for t in timestamp_data:
            if t.get('context') == 'observed':
                ts.append(t.get('iso'))

        return_data['qintel_cve_first_observed'] = None
        return_data['qintel_cve_last_observed'] = None
        return_data['qintel_cve_recently_observed'] = None

        ts = sorted(ts, reverse=False)
        if len(ts) > 0:
            return_data['qintel_cve_first_observed'] = ts[0]
            return_data['qintel_cve_last_observed'] = ts[-1]
            return_data['qintel_cve_recently_observed'] = False
            if ts[-1] > arrow.utcnow().shift(days=-30).isoformat():
                return_data['qintel_cve_recently_observed'] = True

        return return_data

    def _generate_cve_results(self, event, cve_result):

        event_cve = event.get(self.field)
        fields = self._format_cve_data(cve_result.get(event_cve, {}))
        for k, v in fields.items():
            event[k] = v

        return event

    def enrich(self, events, selectors):

        cve_results = {}
        self.kvstore.query_cache(selectors, cve_results)

        if len(selectors) > 0:
            self._init_client()

            pool = ThreadPool(10)
            lookup = lambda cve: self._lookup_cve(cve)
            pmi_results = pool.map(lookup, selectors)

            for result in pmi_results:
                for cve, data in result.items():
                    cve_results[cve] = data

            self.kvstore.write_cache(pmi_results)

        for e in events:
            yield self._generate_cve_results(e, cve_results)
