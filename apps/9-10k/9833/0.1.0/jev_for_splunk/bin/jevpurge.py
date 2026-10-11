#!/usr/bin/env python
"""`| jevpurge`: delete answer-cache entries older than the configured lifetime. Sends nothing anywhere.

Expired entries are already ignored by `| jev`; this only gives the disk space back. The app
runs it once a night from a saved search.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from splunklib.searchcommands import Configuration, GeneratingCommand, dispatch  # noqa: E402

import jev_cache  # noqa: E402
import jev_splunk  # noqa: E402


@Configuration(type="reporting")
class JevPurgeCommand(GeneratingCommand):
    def generate(self):
        try:
            config = jev_splunk.read_settings(self._metadata.searchinfo.session_key)
            jev_cache.Cache(jev_splunk.KV(self.service), lifetime_days=config["cache_days"]).purge()
        except Exception as e:  # "{}": splunklib formats its first argument, and a KV store error quotes a JSON body
            self.write_error("{}", "jevpurge: the cache was not purged: %s: %s" % (type(e).__name__, e))
            sys.exit(1)
        yield {"_time": time.time(), "action": "jev_cache_purge", "cache_days": config["cache_days"]}


dispatch(JevPurgeCommand, sys.argv, sys.stdin, sys.stdout, __name__)
