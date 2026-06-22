#!/usr/bin/env python
"""Custom search command: | terracelookup ip_field=src_ip
Streaming command that enriches events with Terrace threat intelligence.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

from splunklib.searchcommands import (
    Configuration,
    Option,
    StreamingCommand,
    dispatch,
)


# In-memory LRU cache to avoid redundant API calls within a single search.
_cache = {}
_CACHE_MAX = 10000


@Configuration(local=True)
class TerraceLookupCommand(StreamingCommand):
    """Enrich events with Terrace Networks threat intelligence.

    ##Syntax

        ... | terracelookup ip_field=<field_name>

    ##Example

        index=firewall | terracelookup ip_field=src_ip
        | where terrace_classification="malicious"
    """

    ip_field = Option(name="ip_field", require=True)

    def stream(self, records):
        api_key = self._get_api_key()
        if not api_key:
            for record in records:
                record["terrace_error"] = "API key not configured"
                yield record
            return

        from terrace_api import TerraceClient

        client = TerraceClient(api_key=api_key, base_url=self._get_base_url())

        for record in records:
            ip = record.get(self.ip_field)
            if not ip:
                yield record
                continue

            enrichment = self._lookup(client, str(ip))
            if enrichment:
                for key, value in enrichment.items():
                    record[key] = value

            yield record

    def _lookup(self, client, ip):
        """Look up an IP with caching."""
        if ip in _cache:
            return _cache[ip]

        from terrace_api import flatten_ip_detail

        try:
            detail = client.get_ip_detail(ip)
            result = flatten_ip_detail(detail, include_ip=False)
        except Exception:
            result = {"terrace_classification": "unknown", "terrace_error": "lookup_failed"}

        if len(_cache) < _CACHE_MAX:
            _cache[ip] = result
        return result

    def _get_api_key(self):
        for cred in self.service.storage_passwords:
            if cred.realm == "TA-terrace" and cred.username == "api_key":
                return cred.clear_password
        return ""

    def _get_base_url(self):
        return "https://api.terracenetworks.com"


dispatch(TerraceLookupCommand, sys.argv, sys.stdin, sys.stdout, __name__)
