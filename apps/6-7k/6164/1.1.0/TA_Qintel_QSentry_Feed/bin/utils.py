import logging, logging.handlers
import json
import os
from constants import APP_NAME, CONFIG_FILE, KV_WBATCH_SIZE, KV_RBATCH_SIZE, REALM
from splunklib.client import connect, AuthenticationError, HTTPError
from solnlib import conf_manager, credentials
import arrow


def get_config_item(session_key, conf_stanza, item):

    cfm = conf_manager.ConfManager(session_key, APP_NAME, realm=REALM)
    config = cfm.get_conf(CONFIG_FILE)
    root = config.get(conf_stanza, {})
    rv = root.get(item)

    return rv


def get_config(session_key, conf_stanza):

    cfm = conf_manager.ConfManager(session_key, APP_NAME, realm=REALM)
    config = cfm.get_conf(CONFIG_FILE)
    root = config.get(conf_stanza, {})

    return root


def get_credentials(session_key, conf_stanza, pw_item):

    # password from passwords.conf
    cm = credentials.CredentialManager(session_key, APP_NAME, realm=REALM)
    pw = cm.get_password(conf_stanza)
    pw = json.loads(pw)
    pw = pw[pw_item]

    return pw


def setup_logging(session_key):

    log_level = get_config_item(session_key, 'logging', 'loglevel') or 'INFO'

    logger = logging.getLogger()
    logger.setLevel(log_level)

    log_name = '{}.log'.format(APP_NAME)
    log_path = os.path.join(os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', log_name)
    log_format = '%(asctime)s log_level=%(levelname)s, pid=%(process)d, module=%(module)s, func_name=%(funcName)s, ' \
                 'code_line_no=%(lineno)d - %(message)s'

    log_handler = logging.handlers.RotatingFileHandler(log_path, mode='a', maxBytes=2500000, backupCount=7)
    formatter = logging.Formatter(log_format)
    log_handler.setFormatter(formatter)

    logger.addHandler(log_handler)

    return logger


def regex_match(string, pattern):

    for r in pattern:
        if r.match(string):
            return True

    return False


# https://hackersandslackers.com/extract-data-from-complex-json-python/
def extract_json_values(obj, key):
    """Pull all values of specified key from nested JSON."""
    arr = []

    def extract(obj, arr, key):
        """Recursively search for values of key in JSON tree."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    if k == key:
                        arr.extend(v)
                    else:
                        extract(v, arr, key)
                elif k == key:
                    arr.append(v)
        elif isinstance(obj, list):
            for item in obj:
                extract(item, arr, key)
        return arr

    results = extract(obj, arr, key)
    return results


def timerange_check(event_time, first_seen, last_seen, time_window):

    # no timerange, return everything
    if time_window == 0:
        return True

    event_time = arrow.get(event_time).to('UTC')

    first_seen = arrow.get(first_seen)
    last_seen = arrow.get(last_seen)
    lower_range = last_seen.shift(days=-int(time_window))
    upper_range = last_seen.shift(days=+int(time_window))

    if event_time.is_between(first_seen, last_seen, '[]') or \
            event_time.is_between(lower_range, upper_range, '[]'):
        return True

    return False


def chunk(it, slice=50):
    assert(slice > 0)
    a = []

    for x in it:
        if len(a) >= slice :
            yield a
            a = []
        a.append(x)

    if a:
        yield a

class KVStore(object):

    def __init__(self, session_key, logger, kvstore):

        self.logger = logger

        kwargs = {
            'token': session_key,
            'app': APP_NAME,
            'owner': 'nobody'
        }

        try:
            self.service = connect(**kwargs)
        except AuthenticationError as e:
            logger.error('kv store authentication error={}'.format(e))

        self.collection = self.service.kvstore[kvstore]

    def chunk(self, data, chunk_size):

        chunks = []
        for i in range(0, len(data), chunk_size):
            chunks.append(data[i:i + chunk_size])

        return chunks

    def bulk_read(self, key, data):

        results = []

        chunks = self.chunk(data, KV_RBATCH_SIZE)

        for chunk in chunks:

            bulk_query = [{"query": {key: k}} for k in chunk]

            try:
                query_results = self.collection.data.batch_find(*bulk_query)
            except HTTPError as e:
                continue

            results = results + query_results

        return results

    def bulk_update(self, data):

        # need to chunk bc of kvstore batch save limits
        chunks = self.chunk(data, KV_WBATCH_SIZE)

        for chunk in chunks:

            try:
                r = self.collection.data.batch_save(*chunk)
            except Exception as e:
                self.logger.error('action=bulk_kvupdate, error={}'.format(e))
                return False

            return r

        return 0

    def bulk_write(self, data):

        # need to chunk bc of kvstore batch save limits
        chunks = self.chunk(data, KV_WBATCH_SIZE)

        for chunk in chunks:

            try:
                r = self.collection.data.batch_save(*chunk)
            except Exception as e:
                self.logger.error('action=bulk_kvwrite, error={}'.format(e))
                continue

        return len(data)

    def clean(self, query):
        self.collection.data.delete(query=query)

    def query_cache(self, data, results_object):

        cache_results = self.bulk_read('_key', data)
        cache_updates = []

        for r in cache_results:
            if len(r) == 0:
                continue

            # populate results
            results_object[r[0]['_key']] = r[0]['data']
            data.remove(r[0]['_key'])

            # prepare cache updates
            update = {}
            for k, v in r[0].items():
                update[k] = v
            update['last_seen'] = arrow.utcnow().isoformat()
            cache_updates.append(update)

        # write cache updates
        self.bulk_update(cache_updates)

    def write_cache(self, data):

        cache_writes = []
        for result in data:
            for k, v in result.items():
                cache_writes.append({
                    '_key': k,
                    'data': v,
                    'first_seen': arrow.utcnow().isoformat(),
                    'last_seen': arrow.utcnow().isoformat()
                })

        self.bulk_write(cache_writes)
