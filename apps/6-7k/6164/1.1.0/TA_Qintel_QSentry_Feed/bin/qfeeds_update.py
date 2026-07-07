import os
import sys
import json
import time
from itertools import groupby
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
import app_qintel_qsentry_feed_declare
from constants import APP_NAME, FEED_KV_STORE, KV_WBATCH_SIZE, UA
from utils import KVStore, setup_logging, get_config, get_credentials, \
    chunk

from solnlib.credentials import CredentialNotExistException

from qintel_helper import qsentry_feed

if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

from splunk.persistconn.application \
    import PersistentServerConnectionApplication


class UpdateFeeds(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        super(UpdateFeeds, self).__init__()
        self.feed_date = str(datetime.now(timezone.utc).date())
        self.tags_fields = ['service_name', 'service_type']
        self.feed_record_timestamp = datetime.now().isoformat()

    def feeds_config(self, session_key):
        conf = get_config(session_key, 'qsentry_feed')

        try:
            token = get_credentials(session_key, 'qsentry_feed', 'api_key')
        except CredentialNotExistException:
            raise Exception('missing QSentry token')

        remote = conf.get('qsentry_api_url')
        if not remote:
            remote = None

        self.feed_args = {
            'token': token,
            'remote': remote,
            'user_agent': UA,
            'logger': self.logger.warn
        }

    def format_feed_record(self, r):

        tags = [r[field] for field in self.tags_fields if r.get(field)]
        if r.get('criminal'):
            tags.append('criminal')

        rv = {
            '_key': '#'.join([r['ip_address'], r['service_name']]),
            'ip_address': r['ip_address'],
            'qintel_descriptions': r['comment'],
            'qintel_tags': tags,
            'feed_type': 'anon',
            '_feed_time': self.feed_record_timestamp,
            '_feed_date': self.feed_date
        }

        return rv

    def feed_request(self):
        feed_results = []

        try:
        
            self.logger.info(f'action=update_feeds, '
                                f'message=fetching feed date {self.feed_date}')

            for r in qsentry_feed(feed_date=self.feed_date, **self.feed_args):
               yield self.format_feed_record(r)

        except Exception as e:
            self.logger.error(f'action=update_feeds, error={e}')
            raise

        return feed_results

    def handle(self, in_string):

        start_time = time.time()

        data = json.loads(in_string)

        session_key = data['session']['authtoken']
        self.logger = setup_logging(session_key)

        self.kvstore = KVStore(session_key, self.logger, FEED_KV_STORE)

        results_count = 0

        try:
            # build feed requests
            self.feeds_config(session_key)
            self.logger.debug(f'feed_requests is: {self.feed_args}')

            # request feeds
            for batch in chunk(self.feed_request(), KV_WBATCH_SIZE):
                writes = self.kvstore.bulk_write(batch)
                results_count += writes

        except Exception as e:
            self.logger.error('action=update_feeds, error={}'.format(e), exc_info=True)
            return {'payload': 'update_feeds: error', 'status': 400}

        run_time = time.time() - start_time

        self.logger.info('action=update_feeds, status=success, record_count={}'
                         ', runtime={}'.format(results_count, run_time))

        return {'payload': f'update_feeds: {results_count} records, '
                           f'runtime: {run_time}s',
                'status': 200
                }
