import os
import sys
import logging
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
import app_qintel_qsentry_declare
from constants import APP_NAME, QSENTRY_KV_STORE, CACHE_LIMIT, MAX_CACHE_LIMIT
from utils import KVStore, setup_logging

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

        data = json.loads(in_string)
        session_key = data['session']['authtoken']
        logger = setup_logging(session_key)

        self.kvstore = KVStore(session_key, logger, QSENTRY_KV_STORE)

        now = datetime.utcnow()
        lower_limit = (now - timedelta(hours=int(CACHE_LIMIT))).isoformat()
        upper_limit = (now - timedelta(hours=int(MAX_CACHE_LIMIT))).isoformat()

        query = {"$or": [{"last_seen": {"$lt": lower_limit}}, {"first_seen": {"$lt": upper_limit}}]}
        query = json.dumps(query)

        try:
            r = self.kvstore.clean(query)
        except Exception as e:
            logger.error('action=cache_clean, error={}'.format(e))
            return {'payload': 'cache_clean: error', 'status': 400}

        logger.info('action=cache_clean, count={}'.format(r))
        return {'payload': 'cache_clean: {} records'.format(r),
                'status': 200
        }
