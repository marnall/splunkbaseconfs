import os
import sys
import logging
from json import dumps, loads
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
import app_qintel_qsentry_feed_declare
from constants import FEED_KV_STORE
from utils import KVStore, setup_logging, get_config_item

if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

from splunk.persistconn.application import PersistentServerConnectionApplication


class Clean(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        pass

    def handle(self, in_string):
    
        data = loads(in_string)
        session_key = data['session']['authtoken']
        logger = setup_logging(session_key)

        logger.info('action=feed_clean, status=starting')

        self.kvstore = KVStore(session_key, logger, FEED_KV_STORE)

        max_feed_age = int(get_config_item(session_key, 'qsentry_feed', 'feed_age'))

        today = datetime.now(timezone.utc)
        lower_limit = (today - timedelta(days=int(max_feed_age))).strftime('%Y-%m-%d')

        query = {"_feed_date": {"$lte": lower_limit}}

        try:
            self.kvstore.clean(dumps(query))
        except Exception as e:
            logger.error('action=feed_clean, error={}'.format(e))
            return {'payload': 'feed_clean: error', 'status': 400}

        logger.info('action=feed_clean, status=complete')

        return {'payload': 'feed_clean: complete', 'status': 200}
